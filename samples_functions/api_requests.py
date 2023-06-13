import pip

import sys
import json
import csv
import gzip
import re
import math
import pandas as pd
import openai
import tiktoken

from tqdm import tqdm
from argparse import ArgumentParser

MAX_LINES = 207614

QUESTION = "Please correct the OCR noise in the following text and provide the corrected version, do not translate or complete the text. Give an answer in this format 'Answer: \"text\"'. Here's the text:\n\"{}\""

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--ids', required=True)
    ap.add_argument('--language', required=True, choices=['FR', 'EN', 'FI'])
    ap.add_argument('--api-key', required=True)
    ap.add_argument('--model', default="gpt-3.5-turbo")
    ap.add_argument('--fixed-output', required=True)
    ap.add_argument('--unfixed-output', required=True)
    ap.add_argument('--debug-log')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int)
    ap.add_argument('--replace', type=str, default='False')
    ap.add_argument('--check', type=str)
    return ap

def str2bool(s):
    if s.lower() in ['true', 't', 'y', 'yes', '1']:
        return True
    return False

def token_count(text, language, model):
    prompt = QUESTION.format(text)
    encoding = tiktoken.encoding_for_model(model)
    token_count = len(encoding.encode("user")) + len(encoding.encode(prompt)) + 6
    return token_count

def pattern_matching(text, ocr_text):
    if text.lower().startswith('answer: '):
        res = text.strip()[8:].strip()
        if res.startswith('"') and not ocr_text.strip().startswith('"'):
            res = res[1:]
        if res.endswith('"') and not ocr_text.strip().endswith('"'):
            res = res[:-1]
    elif text.strip().startswith('"') and text.strip().endswith('"'):
        res = text.strip()[1:-1]
    else:
        return False, text
    return True, res

def correct_ocr_noise(text, language, key, model, index, log, total_tokens):
    prompt = QUESTION.format(text)
    messages = [{"role": "user", "content":prompt}]
    try:
        openai.api_key = key
        response = openai.ChatCompletion.create(model = model, messages = messages, max_tokens=450)
        if log is not None:
            response_json = response.to_dict()
            response_json['question'] = prompt
            response_json['index'] = index
            with open(log, 'a') as f:
                f.write(json.dumps(response_json))
                f.write('\n')
        result = response["choices"][0]["message"]["content"]
        tokens = response["usage"]["total_tokens"]
        b, text = pattern_matching(result, text)
        return b, text, tokens
    except openai.OpenAIError as e:
        sys.stderr.write(f"OpenAIError occured at index: {index} (OCR correction)\n")
        sys.stderr.write(f"Error message: {str(e)}\n")
        sys.stderr.write(f"Total tokens: {total_tokens} (cost: ${0.002 * total_tokens / 1000} for gpt-3.5-turbo)\n")
        return index - 1
    except Exception as e:
        sys.stderr.write(f"Error occured at index: {index} (OCR correction)\n")
        sys.stderr.write(f"Error message: {str(e)}\n")
        sys.stderr.write(f"Total tokens: {total_tokens} (cost: ${0.002 * total_tokens / 1000} for gpt-3.5-turbo)\n")
        return index - 1

def get_ids(jsonl, start):
    ids = []
    with open(jsonl, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= start:
                json_data = json.loads(line)
                index = json_data.get('index')
                text_id = json_data.get('id')
                chunk_id = json_data.get('chunk')
                ocr_text = json_data.get('input')
                ids.append((index, text_id, chunk_id, ocr_text))
    return ids

def get_language(language):
    language_names = {
        'EN': 'English',
        'FI': 'Finnish',
        'FR': 'French'
    }
    if language in language_names:
        return language_names[language]
    else:
        print("Supported languages:")
        for code, name in language_names.items():
            print(f"{code}")
        raise ValueError(f"Unsupported language: {language}")

def get_api_key(key_file):
    with open(key_file, 'rt') as file:
        api_key = file.read().strip()
    return api_key

def save_pairs(jsonl_file, ocr_text, text, index, text_id, chunk_id, tokens):
    updated = False
    
    with open(jsonl_file, 'rt', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        if data.get('index') == index:
            data['input'] = ocr_text
            data['output'] = text
            data['text_id'] = text_id
            data['chunk_id'] = chunk_id
            data['output_size'] = len(text)
            data['tokens'] = tokens
            lines[i] = json.dumps(data) + '\n'
            updated = True
            break
    if not updated:
        data = {
            "input": ocr_text,
            "output": text,
            "index": index,
            "text_id": text_id,
            "chunk_id": chunk_id,
            "output_size": len(text),
            "tokens": tokens
        }
        lines.append(json.dumps(data) + '\n')
    
    with open(jsonl_file, 'wt', encoding='utf-8') as f:
        f.writelines(lines)

def remove_by_index(jsonl_file, index):
    lines_to_keep = []
    
    with open(jsonl_file, 'rt', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get('index') != index:
                lines_to_keep.append(line)
    
    with open(jsonl_file, 'wt', encoding='utf-8') as f:
        f.writelines(lines_to_keep)

def get_processed_indexes(fixed_jsonl, unfixed_jsonl, ids, replace):
    processed_indexes = []
    if not replace:
        with open(fixed_jsonl, 'rt', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                index = data.get('index')
                if index in [item[0] for item in ids]:
                    processed_indexes.append(index)
        with open(unfixed_jsonl, 'rt', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                index = data.get('index')
                if index in [item[0] for item in ids]:
                    processed_indexes.append(index)
    filtered_ids = [x for x in ids if x[0] not in processed_indexes]
    dataframe = pd.DataFrame({
        'index': [x[0] for x in filtered_ids],
        'id': [x[1] for x in filtered_ids],
        'chunk': [x[2] for x in filtered_ids],
        'input': [x[3] for x in filtered_ids]
    })
    return dataframe, processed_indexes
        
def check_index(jsonl_file, index):
    with open(jsonl_file, 'rt', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get('index') == index:
                return True
    return False

def estimate_cost(df, language, model):
    total_tokens = 0
    for _, row in df.iterrows():
        ocr_text = row['input']
        tokens = token_count(ocr_text, language, model)
        total_tokens += tokens
    cost = 0.002 * total_tokens / 1000
    print(f"There are {total_tokens} tokens ({len(df)} texts), so it should cost ${cost} with gpt-3.5-turbo (question only, so for the total cost, expect to pay twice as much)")

def main(argv):
    args = argparser().parse_args()
    
    ids = get_ids(args.ids, args.start) # Set of IDs (indexes, text IDs and chunk IDs)
    language = get_language(args.language) # Set the language of the QUESTION for the API
    key = get_api_key(args.api_key)
    model = args.model
    replace = str2bool(args.replace)
    log = args.debug_log
    
    if args.limit:  # For test
        ids = ids[:args.limit]
    
    dataframe, processed_indexes = get_processed_indexes(args.fixed_output, args.unfixed_output, ids, replace)
    print(len(ids))
    print(len(dataframe))
    print(args.start, args.limit)
    
    estimate_cost(dataframe, language, model)
    
    if args.check is None:
        return 0
    
    check = str2bool(args.check)
    if check:
        user_input = input("Do you still want to continue the script? (y/n): ")
    else:
        user_input = 'y'
    if user_input.lower() != 'y':
        print("Script execution stopped.")
        return
    
    total_tokens = 0
    
    try:
        for _, row in tqdm(dataframe.iterrows(), total=len(dataframe), desc="Samples created"):
            index = row['index']
            text_id = row['id']
            chunk_id = row['chunk']
            ocr_text = row['input']
            
            try:
                text = ocr_text
                b, text, tokens = correct_ocr_noise(ocr_text, language, key, model, index, log, total_tokens)
                total_tokens += tokens
                #if b:
                #    save_pairs(args.fixed_output, ocr_text, text, index, text_id, chunk_id, tokens)
                #    remove_by_index(args.unfixed_output, index)
                #else:
                #    save_pairs(args.unfixed_output, ocr_text, text, index, text_id, chunk_id, tokens)
                #    remove_by_index(args.fixed_output, index)
            except Exception as e:
                sys.stderr.write(f"Error occured at index: {index}\n")
                sys.stderr.write(f"Error message: {str(e)}\n")
                sys.stderr.write(f"Total tokens: {total_tokens} (cost: ${0.002 * total_tokens / 1000} for gpt-3.5-turbo)\n")
    except Exception as e:
        sys.stderr.write("An error occured during processing.\n")
        sys.stderr.write(f"Error message: {str(e)}\n")
        return -1
        
    print(f"Total tokens: {total_tokens} (cost: ${0.002 * total_tokens / 1000} for gpt-3.5-turbo)")
    return dataframe['index'].max()

if __name__ == "__main__":
    sys.exit(main(sys.argv))