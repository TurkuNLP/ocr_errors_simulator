import Levenshtein as LV
import json
import pandas as pd
import csv
import sys
import os
import re
import unicodedata

from glob import glob
from tqdm import tqdm
from argparse import ArgumentParser

import OCR_errors_JSON_generator_functions as ocr

def argparser():
    ap = ArgumentParser()
    ap.add_argument('jsonl', nargs='+')
    ap.add_argument('--charset', required=True)
    ap.add_argument('--output-jsonl', required=True)
    return ap

def preprocessing_text(text):
    text = re.sub('[\n\t]', ' ', text)
    text = text.strip()
    text = re.sub(' +', ' ', text)
    text = ''.join(c for c in text if unicodedata.category(c) == 'Zs' or c.isprintable())
    return text

def get_dataframe(jsonl_files):
    l = []
    for jsonl_file in jsonl_files:
        with open(jsonl_file, 'rt', encoding='utf-8') as f:
            for line in f:
                json_obj = json.loads(line)
                l.append((preprocessing_text(json_obj.get('input')), preprocessing_text(json_obj.get('output'))))
    columns = ['input', 'output']
    return pd.DataFrame(l, columns=columns)

def add_charset(charset_name, json_content):
    with open(charset_name, 'r') as charset:
        while (char := charset.read(1)):
            ocr.update_unknown_char(json_content, char, 1, 1)
    return json_content

def add_data(df, json_content):
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Data processing   ", unit=" pairs"):
        ocr.add_data_to_json(row['input'], row['output'], json_content)
    return json_content

def save_data(json_content, output_jsonl):
    with open(output_jsonl, 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(json_content, indent=4))
        

def main(argv):
    args = argparser().parse_args()
    jsonl_files = args.jsonl
    charset_name = args.charset
    output_jsonl = args.output_jsonl
    
    df = get_dataframe(jsonl_files)
    
    json_content = {}
    ocr.init_json_file(df, json_content)
    
    json_content = add_charset(charset_name, json_content)
    
    json_content = add_data(df, json_content)
    save_data(json_content, output_jsonl)
    
    ocr.int_to_probabilities(output_jsonl)
    ocr.json2jsonl(output_jsonl, output_jsonl)

if __name__ == "__main__":
    sys.exit(main(sys.argv))