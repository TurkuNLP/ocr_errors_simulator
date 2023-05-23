import sys
import json
import csv
import gzip
import re
import math
import pandas as pd
import openai

from tiktoken
from tqdm import tqdm
from argparse import ArgumentParser

MAX_LINES = 207614

QUESTION = "If possible, please correct the OCR noise in the following {} text and provide the corrected version in an answer which should look like this 'ANSWER: \"text\"'. Here's the text:\n\"{}\""

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--ids', required=True)
    ap.add_argument('--language', required=True, choices=['FR', 'EN', 'FI'])
    ap.add_argument('--api-key', required=True)
    ap.add_argument('--model', default="gpt-3.5-turbo")
    ap.add_argument('--fixed-output', required=True)
    ap.add_argument('--unfixed-output', required=True)
    ap.add_argument('--text-chunk', type=int, default=1000)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int)
    ap.add_argument('jsonl')
    return ap

def cut_text(text, size):
    if len(text) <= size:
        return text
    return text[:size]

def token_cost(text, language, key, model):
    tokenizer = tiktoken.Tokenizer(tokenizer=model)
    question = QUESTION.format(language, text)
    token_count = tokenizer.count_tokens(question)
    return token_count

def correct_ocr_noise(text, language, key, model):
    response = openai.Completion.create(
        model = model,
        prompt = QUESTION.format(language, text))
    
    if response.choices[0].text.startswith('ANSWER: '):
        corrected_text = response.choices[0].text.strip()[8:]
        if corrected_text.startswith('"') and corrected_text.endswith('"'):
            corrected_text = corrected_text[1:-1]
        return corrected_text
    else:
        return False

def get_id(url):
    match = re.search(r'(\d+)\.txt$', url)
    if match:
        id_with_extension = match.group(1)
        id_without_extension = id_with_extension[:-4] if id_with_extension.endswith('.txt') else id_with_extension
        try:
            id_as_int = int(id_without_extension)
            return id_as_int
        except ValueError:
            print("Not int")
            return None
    else:
        #print(f"Not found ({url})")
        return None

def get_ids(jsonl, start):
    ids = []
    with open(jsonl, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= start:
                json_data = json.loads(line)
                index = json_data.get('index')
                text_id = json_data.get('id')
                chunk_id = json_data.get('chunk')
                ids.append((index, text_id, chunk_id))
    return ids

def get_texts(ids, args, size):
    if args.limit:
        iteration_count = 0
    texts = []
    with gzip.open(args.jsonl, 'rt', encoding='utf-8') as f:
        pbar_lines = tqdm(total=MAX_LINES, desc="Lines")
        pbar_texts = tqdm(total=len(ids), desc="Texts")
        for line in f:
            json_data = json.loads(line)
            url = json_data['url']
            text_id = get_id(url)

            matching_ids = [(id_tuple[1], id_tuple[2]) for id_tuple in ids if id_tuple[1] == text_id]
            if matching_ids:
                chunk_id = matching_ids[0][1]
                text = cut_text(json_data['text'], size)
                texts.append(text)
                pbar_texts.update(1)

                if args.limit:
                    iteration_count += 1
                    if iteration_count >= args.limit:
                        break
            pbar_lines.update(1)
        pbar_texts.close()
        pbar_lines.close()
    return texts

def get_language(language):
    language_names = {
        'EN': 'English',
        'FI': 'Finnish',
        'FR': 'French'
    }
    if language in language_names:
        return language_names[language]
    else:
        sys.stderr.write("Supported languages:\n")
        for code, name in language_names.items():
            sys.stderr.write(f"{code}\n")
        raise ValueError(f"Unsupported language: {language}")

def get_api_key(key_file):
    with open(key_file, "r") as file:
        api_key = file.read().strip()
    return api_key

def save_pairs(jsonl_file, ocr_text, text, index, text_id, chunk_id):
    updated = False
    
    with open(jsonl_file, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        if data.get('index') == index:
            data['input'] = ocr_text
            data['output'] = text
            data['text_id'] = text_id
            data['chunk_id'] = chunk_id
            lines[i] = json.dumps(data) + '\n'
            updated = True
            break
    if not updated:
        data = {
            "input": ocr_text,
            "output": text,
            "index": index,
            "text_id": text_id,
            "chunk_id": chunk_id
        }
        lines.append(json.dumps(data) + '\n')
    
    with open(jsonl_file, 'w') as f:
        f.writelines(lines)

def remove_by_index(jsonl_file, index):
    lines_to_keep = []
    
    with open(jsonl_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data.get('index') != index:
                lines_to_keep.append(line)
    
    with open(jsonl_file, 'w') as f:
        f.writelines(lines_to_keep)

def main(argv):
    args = argparser().parse_args()
    
    ids = get_ids(args.ids, args.start) # Set of IDs (indexes, text IDs and chunk IDs)
    size = args.text_chunk # Size of the chunk (must be the same used in gets_ids_from_ecco.py)
    language = get_language(args.language)
    key = get_api_key(args.api_key)
    
    if args.limit:  # For test
        ids = ids[:args.limit]
    
    texts = get_texts(ids, args, size)
    
    sys.stderr.write(f"{len(ids)}; {len(texts)}\n")
    dataframe = pd.DataFrame({'index': [x[0] for x in ids], 'id': [x[1] for x in ids], 'chunk': [x[2] for x in ids], 'input': texts})
    
    try:
        for _, row in tqdm(dataframe.iterrows(), total=len(dataframe)):
            index = row['index']
            text_id = row['id']
            chunk_id = row['chunk']
            ocr_text = row['input']
            
            try:
                #text = correct_ocr_noise(ocr_text, language)
                text = ocr_text
                if text:
                    save_pairs(args.fixed_output, ocr_text, text, index, text_id, chunk_id)
                    remove_by_index(args.unfixed_output, index)
                else:
                    save_pairs(args.unfixed_output, ocr_text, text, index, text_id, chunk_id)
                    remove_by_index(args.fixed_output, index)
            except Exception as e:
                sys.stderr.write(f"Error occured at index: {index}\n")
                sys.stderr.write(e + "\n")
                return index - 1
        except Exception as e:
            sys.stderr.write("An error occured during processing.\n")
            sys.stderr.write(e + "\n")
            return -1
        
        return dataframe['index'].max()

if __name__ == "__main__":
    sys.exit(main(sys.argv))