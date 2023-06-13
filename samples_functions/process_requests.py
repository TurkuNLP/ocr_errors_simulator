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

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--ids', required=True)
    ap.add_argument('--fixed-output', required=True)
    ap.add_argument('--unfixed-output', required=True)
    ap.add_argument('--debug-log')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int)
    ap.add_argument('--replace', type=str, default='False')
    ap.add_argument('--check', type=str)
    return ap

def pattern_matching(text, ocr_text):
    prefixes = {
        'answer:': 7,
        'correction:': 11,
        'corrected text:': 15
    }
    for prefix, length in prefixes.items():
        if text.lower().startswith(prefix):
            res = text.strip()[length:].strip()
            if res.startswith('"') and not ocr_text.strip().startswith('"'):
                res = res[1:]
            if res.endswith('"') and not ocr_text.strip().endswith('"'):
                res = res[:-1]
            return True, res
    if text.strip().startswith('"') and text.strip().endswith('"'):
        res = text.strip()[1:-1]
        return True, res
    return False, text

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

def retrieve_data_from_index(ids, index):
    for data in ids:
        if data[0] == index:
            return data[1], data[2], data[3]

def get_dataframe_from_items(items):
    columns = ['index', 'text', 'ocr_text', 'text_id', 'chunk_id', 'tokens', 'bool']
    df = pd.DataFrame(items, columns=columns)
    df = df.drop_duplicates(subset='index', keep='last')
    return df
        
def get_responses_dataframe(log, ids):
    items = []
    with open(log, 'r') as f:
        for line in tqdm(f, desc="Samples retrieved"):
            json_data = json.loads(line)
            index = json_data['index']
            tokens = json_data['usage']['total_tokens']
            response = json_data['choices'][0]['message']['content']
            text_id, chunk_id, ocr_text = retrieve_data_from_index(ids, index)

            items.append((index, response, ocr_text, text_id, chunk_id, tokens, False))
    dataframe = get_dataframe_from_items(items)
    return dataframe

def save_samples(output_file, df):
    print(len(df))
    with open(output_file, 'wt', encoding='utf-8') as f:
        for _, row in df.iterrows():
            json_data = {
                "input": row['ocr_text'],
                "output": row['text'],
                "index": row['index'],
                "text_id": row['text_id'],
                "chunk_id": row['chunk_id'],
                "output_size": len(row['text']),
                "tokens": row['tokens']
            }
            f.write(json.dumps(json_data) + '\n')
    return 0
    
def main(argv):
    args = argparser().parse_args()

    ids = get_ids(args.ids, 0) # Set of IDs (indexes, text IDs and chunk IDs)
    log = args.debug_log

    dataframe = get_responses_dataframe(log, ids)

    wrong = 0
    for i, row in dataframe.iterrows():
        response = row['text']
        ocr_text = row['ocr_text']
        row['bool'], row['text'] = pattern_matching(response, ocr_text)
        index, text_id, chunk_id, tokens = row['index'], row['text_id'], row['chunk_id'], row['tokens']
        if not row['bool']:
            wrong += 1
            print(wrong, len(response), '###', response[:25], '[...]', response[-25:], '###')
        dataframe.loc[i] = row

    save_samples(args.fixed_output, dataframe[dataframe['bool']])
    save_samples(args.unfixed_output, dataframe[-dataframe['bool']])

if __name__ == "__main__":
    sys.exit(main(sys.argv))