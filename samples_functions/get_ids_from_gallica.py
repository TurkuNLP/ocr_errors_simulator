import sys
import os
import json
import csv
import gzip
import re
import math
import pandas as pd
import random
import glob

from tqdm import tqdm
from argparse import ArgumentParser

MAX_LINES = 207614

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--nb-ids', type=float, default=5000)
    ap.add_argument('--jsonl-gallica', required=True)
    ap.add_argument('--chunk-size', type=int, default=1000)
    ap.add_argument('--seed', type=int)
    ap.add_argument('jsonl', nargs='+')
    return ap

def cut_text(text, size, chunk):
    if len(text) <= size:
        return text
    start_index = size * chunk
    end_index = start_index + size
    return text[start_index:end_index]

def get_id(name, jsonl_file, line_num):
    return (os.path.basename(jsonl_file).split('/')[-1], line_num, name)

def save_sets(gallica_sets, args):
    with open(args.jsonl_gallica, 'w') as f:
        for idx, (id, chunk_id, chunk_text) in enumerate(gallica_sets):
            json.dump({"index": idx, "id": id, "chunk": chunk_id, "input": chunk_text}, f)
            f.write('\n')

def get_chunks(text, chunk_size):
    text_length = len(text)
    num_chunks = math.ceil(text_length / chunk_size)
    last_chunk = text_length % chunk_size
    
    if last_chunk < chunk_size:
        num_chunks -= 1
    return num_chunks

def get_random_chunks(num_chunks, desired_num_chunks):
    return random.sample(range(num_chunks), desired_num_chunks)

def add_ids(data_gallica, text_id, num_chunks, text, size):
    desired_num_chunks = 1
    if (num_chunks >= desired_num_chunks):
        random_chunks = get_random_chunks(num_chunks, 1)
        for chunk_id in random_chunks:
            text_chunk = cut_text(text, size, chunk_id)
            data_gallica.append((text_id, chunk_id, text_chunk))

def get_ids(jsonl_files, chunk_size):
    data_gallica = []
    pattern = r"Le taux de reconnaissance estimé pour ce document est de (\d+)%.\n"
    
    for jsonl_file in tqdm(jsonl_files, total=len(jsonl_files), desc="JSONL files"):
        with gzip.open(jsonl_file, 'rt') as f:
            for _ in range(2):
                next(f)
            for line_num, line in enumerate(tqdm(f, desc="Texts")):
                json_data = json.loads(line)
                name = json_data['name']
                text = json_data['text']
                match = re.search(pattern, text)
                if match:
                    text = text[match.end():]
                text = text.replace("[texte_manquant]", "")
                text_id = get_id(name, jsonl_file, line_num)
                num_chunks = get_chunks(text, chunk_size)
            
                add_ids(data_gallica, text_id, num_chunks, text, chunk_size)
                
    return data_gallica

def get_jsonl_files(jsonl_files_name):
    jsonl_files = []
    for pattern in jsonl_files_name:
        if '*' in pattern:
            jsonl_files.extend(glob.glob(pattern))
        else:
            jsonl_files.append(pattern)
    return jsonl_files

def main(argv):
    args = argparser().parse_args()
    
    if (args.seed):
        random.seed(args.seed)
    
    nb_ids = int(args.nb_ids)
    
    jsonl_files = get_jsonl_files(args.jsonl)
    
    data_gallica = get_ids(jsonl_files, args.chunk_size)
    
    indices = list(range(len(data_gallica)))
    
    random.shuffle(indices)
    
    gallica_sets = [data_gallica[i] for i in sorted(indices[:nb_ids])]
    
    save_sets(gallica_sets, args)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
