import sys
import json

import numpy as np

from string import ascii_letters, digits, punctuation
from argparse import ArgumentParser

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--mean', type=float, default=0.1)
    ap.add_argument('--stdev', type=float, default=0.1)
    ap.add_argument('--min-error-prob', type=float, default=0.0)
    ap.add_argument('--max-error-prob', type=float, default=0.5)
    ap.add_argument('--charset_probs', required=True)
    ap.add_argument('jsonl', nargs='+')
    return ap

def get_other_char(char, op, probs_dict, p_char):
    cumu_p = 0
    for c in probs_dict[char][op + '_CHAR']:
        cumu_p += probs_dict[char][op + '_CHAR'][c]
        if p_char <= cumu_p:
            if c == 'SPACE_CHAR':
                return ' '
            return c
    return char

def add_noise(text, rng, args, probs_dict):
    prob = rng.normal(args.mean, args.stdev)
    prob = min(max(prob, args.min_error_prob), args.max_error_prob)
    
    chars = []
    for c in text:
        if rng.random() > prob:
            chars.append(c)
        else:
            p_op = rng.random()
            if c not in probs_dict or (c == ' ' and SPACE_CHAR not in probs_dict):
                working_c = 'OTHER_CHAR'
            else:
                working_c = c
            if p_op < probs_dict[working_c]['DELETE']:
                pass
            elif p_op < (probs_dict[working_c]['DELETE'] + probs_dict[working_c]['REPLACE']):
                p_char = rng.random()
                chars.append(get_other_char(working_c, 'REPLACE', probs_dict, p_char))
            else:
                p_char = rng.random()
                chars.append(get_other_char(working_c, 'INSERT', probs_dict, p_char))
                chars.append(c)
            
    return ''.join(chars)

def main(argv):
    args = argparser().parse_args()
    
    with open(args.charset_probs) as probs_file:
        probs_dict = {}
        for line in probs_file:
            data = json.loads(line)
            char = list(data.keys())[0]
            probs_dict[char] = data[char]
    
    rng = np.random.default_rng(args.seed)
    
    for fn in args.jsonl:
        with open(fn) as f:
            for line in f:
                indata = json.loads(line)
                text = indata['text']
                noised = add_noise(text, rng, args, probs_dict)
                outdata = { 'input': text, 'output': noised }
                print(json.dumps(outdata, ensure_ascii=False))
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))