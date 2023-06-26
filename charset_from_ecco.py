import sys
import json
import gzip
import subprocess
import os
import re
import unicodedata
import time

import numpy as np

from argparse import ArgumentParser
from collections import Counter
from multiprocessing import Pool, Lock

def argparser():
    ap = ArgumentParser()
    ap.add_argument('input_dir', help='Input directory with jsonl files')
    ap.add_argument('--processes', type=int, default=4, help='Number of processes to use')
    return ap

def update_charset(charset, text):
    prepared_text = ''.join(c for c in text if unicodedata.category(c) == 'Zs' or c.isprintable())
    charset.update(prepared_text)

def process_file(jsonl_file):
    charset = Counter()
    with open(jsonl_file, 'r') as f:
        for line in f:
            indata = json.loads(line)
            text = indata['text']
            update_charset(charset, text)
    return charset

def update_progress(p, start_time):
    elapsed_time = time.time() - start_time
    hours = int(elapsed_time / 3600)
    minutes = int(elapsed_time / 60) % 60
    seconds = elapsed_time % 60
    sys.stderr.write(f"json_file done: {p:.2%} ({hours:02d}:{minutes:02d}:{seconds:06.03f})\n")
    
def main(argv):
    args = argparser().parse_args()
    
    jsonl_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.jsonl')]
    total_files = len(jsonl_files)
    
    start_time = time.time()
    
    with Pool(processes=args.processes) as pool:
        charsets = []
        for i, charset in enumerate(pool.imap_unordered(process_file, jsonl_files)):
            update_progress((i+1) / len(jsonl_files), start_time)
            charsets.append(charset)
    
    charset = Counter()
    for cs in charsets:
        charset.update(cs)
    chars = sorted(charset.keys())
    
    for c in chars:
        print(c, end='')
        sys.stderr.write(f"{c}")
    sys.stderr.write("\n")

if __name__ == '__main__':
    sys.exit(main(sys.argv))