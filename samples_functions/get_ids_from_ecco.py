import sys
import json
import csv
import gzip
import re
import math
import pandas as pd
import random

from tqdm import tqdm
from argparse import ArgumentParser

MAX_LINES = 207614

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--nb-ids', type=float, default=5000)
    ap.add_argument('--jsonl-i', required=True)
    ap.add_argument('--jsonl-ii', required=True)
    ap.add_argument('--chunk-size', type=int, default=1000)
    ap.add_argument('--seed', type=int)
    ap.add_argument('jsonl')
    return ap

def cut_text(text, size, chunk):
    if len(text) <= size:
        return text
    start_index = size * chunk
    end_index = start_index + size
    return text[start_index:end_index]

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
        ("Not found")
        return None
    
def save_sets(ecco_i_sets, ecco_ii_sets, args):
    with open(args.jsonl_i, 'w') as f:
        for idx, (id, chunk_id, chunk_text) in enumerate(ecco_i_sets):
            json.dump({"index": idx, "id": id, "chunk": chunk_id, "input": chunk_text}, f)
            f.write('\n')
    with open(args.jsonl_ii, 'w') as f:
        for idx, (id, chunk_id, chunk_text) in enumerate(ecco_ii_sets):
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

def add_ids(data_ecco, text_id, num_chunks, text, size):
    desired_num_chunks = 1
    if (num_chunks >= desired_num_chunks):
        random_chunks = get_random_chunks(num_chunks, 1)
        for chunk_id in random_chunks:
            text_chunk = cut_text(text, size, chunk_id)
            data_ecco.append((text_id, chunk_id, text_chunk))
            
def get_ids(jsonl_file, chunk_size):
    data_ecco_i = []
    data_ecco_ii = []
    
    with gzip.open(jsonl_file, 'rt') as f:
        for line in tqdm(f, total=MAX_LINES):
            json_data = json.loads(line)
            url = json_data['url']
            text = json_data['text']
            text_id = get_id(url)
            num_chunks = get_chunks(text, chunk_size)
            
            if '/ECCO_I/' in url:
                add_ids(data_ecco_i, text_id, num_chunks, text, chunk_size)
            elif '/ECCO_II/' in url:
                add_ids(data_ecco_ii, text_id, num_chunks, text, chunk_size)
                
    return data_ecco_i, data_ecco_ii
            

def main(argv):
    args = argparser().parse_args()
    
    if (args.seed):
        random.seed(args.seed)
    
    nb_ids = args.nb_ids
    
    data_ecco_i, data_ecco_ii = get_ids(args.jsonl, args.chunk_size)
    
    indices_i = list(range(len(data_ecco_i)))
    indices_ii = list(range(len(data_ecco_ii)))
    
    random.shuffle(indices_i)
    random.shuffle(indices_ii)
    
    ecco_i_sets = [data_ecco_i[i] for i in sorted(indices_i[:nb_ids])]
    ecco_ii_sets = [data_ecco_ii[i] for i in sorted(indices_ii[:nb_ids])]
    
    save_sets(ecco_i_sets, ecco_ii_sets, args)
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))
