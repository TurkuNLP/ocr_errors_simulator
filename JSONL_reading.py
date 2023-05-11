import sys
import json
import gzip
import subprocess
import os

import numpy as np

from argparse import ArgumentParser

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--output-dir', default='output')
    ap.add_argument('--nb-lines', type=int, default=10)
    ap.add_argument('jsonl', nargs='+')
    return ap

def save(block, outfile):
    with open(outfile, 'wt') as out_f:
        for line in block:
            out_f.write(json.dumps(line) + '\n')
            
def empty_dir(dir_name):
    for f in os.listdir(dir_name):
        f = os.path.join(dir_name, f)
        if os.path.isfile(f):
            os.remove(f)

def main(argv):
    args = argparser().parse_args()
    
    total_files = len(args.jsonl)
    total_lines = 0
    
    empty_dir(args.output_dir)
    
    nb_line = args.nb_lines
    
    for n, fn in enumerate(args.jsonl):
        with gzip.open(fn, 'rt') as f:
            #cmd = f"zcat {fn} | wc -l"
            #output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            #n_lines = int(output.strip())
            
            n_lines = 207614
            total_lines += n_lines
            f.seek(0)
            
            index = 0
            block = []
            for i, line in enumerate(f):
                indata = json.loads(line)
                block.append(indata)
                if len(block) == nb_line:
                    outfile = os.path.join(args.output_dir, f"ecco_{nb_line*index}_{nb_line*(index+1)}.jsonl")
                    save(block, outfile)
                    index += 1
                    block = []
                print(f"{n+1}/{total_files}\t{(100*(i+1)/n_lines):.2f}%")

if __name__ == '__main__':
    sys.exit(main(sys.argv))