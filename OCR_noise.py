import sys
import json

import numpy as np

from string import ascii_letters, digits, punctuation
from argparse import ArgumentParser

# Default set of characters that can be substituted for
DEFAULT_CHARSET = ascii_letters + digits + punctuation + ' '

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--mean', type=float, default=0.1)
    ap.add_argument('--stdev', type=float, default=0.1)
    ap.add_argument('--min-error-prob', type=float, default=0.0)
    ap.add_argument('--max-error-prob', type=float, default=0.5)
    ap.add_argument('--delete-prob', type=float, default=0.1)
    ap.add_argument('--insert-prob', type=float, default=0.1)
    ap.add_argument('--charset', default=DEFAULT_CHARSET)
    ap.add_argument('--charset_probs', required=True)
    ap.add_argument('--min-block-size', type=int, default=500)
    ap.add_argument('--max-block-size', type=int, default=2000)
    ap.add_argument('--other-char-prob', type=float, default=0.05)
    ap.add_argument('jsonl', nargs='+')
    return ap

def get_op_char(rng, args, char, op, probs_dict, other_chars):
    if rng.random() < args.other_char_prob:
        return get_other_char(rng, other_chars)
    cumu_p = 0
    p_char = rng.random()
    for c in probs_dict[char][op + '_CHAR']:
        cumu_p += probs_dict[char][op + '_CHAR'][c]
        if p_char <= cumu_p:
            if c != 'SPACE_CHAR':
                return c
            return ' '
    return char

def get_other_char(rng, other_chars):
    other_char = rng.choice(other_chars)
    if other_char != 'SPACE_CHAR':
        return other_char
    return ' '

def set_other_chars(probs_dict):
    other_chars = [c for c in DEFAULT_CHARSET]
    for other_char in probs_dict:
        if other_char != 'OTHER_CHAR' and other_char not in other_chars:
            a = 1
            other_chars.append(other_char)
    for other_char in probs_dict['OTHER_CHAR']['REPLACE_CHAR']:
        if other_char not in other_chars:
            a = 1
            other_chars.append(other_char)
    for other_char in probs_dict['OTHER_CHAR']['INSERT_CHAR']:
        if other_char not in other_chars:
            a = 1
            other_chars.append(other_char)
    return other_chars

def set_prob(rng, args):
    prob = rng.normal(args.mean, args.stdev)
    prob = min(max(prob, args.min_error_prob), args.max_error_prob)
    return prob

def generate_block_sizes(text, text_len, min_block_size, max_block_size):
    rng = np.random.default_rng()
    block_sizes = []
    remaining_len = text_len
    text_pos = 0
    while remaining_len > 0:
        block_size = rng.integers(min_block_size, max_block_size)
        if block_size > remaining_len:
            block_size = remaining_len
        space_pos = text.find(' ', text_pos + block_size)
        if space_pos != -1:
            block_size = space_pos - text_pos + 1
        else:
            block_size = remaining_len
        block_sizes.append(block_size)
        remaining_len -= block_size
        text_pos += block_size
    return block_sizes


def generate_blocks(text, block_sizes):
    blocks = []
    start = 0
    for block_size in block_sizes:
        end = start + block_size
        blocks.append(text[start:end])
        start = end
    return blocks

def get_working_char(c, probs_dict):
    if c not in probs_dict or (c == ' ' and SPACE_CHAR not in probs_dict):
        return 'OTHER_CHAR'
    else:
        return c

def add_noise(text, rng, args, probs_dict, other_chars):
    block_sizes = generate_block_sizes(text, len(text), args.min_block_size, args.max_block_size)
    blocks = generate_blocks(text, block_sizes)
    
    chars = []
    
    for text_block in blocks:
        prob = set_prob(rng, args)
        for c in text_block:
            working_c = get_working_char(c, probs_dict)
            if rng.random() > prob * probs_dict[working_c]['KEEP']:
                chars.append(c)
            else:
                p_op = rng.random()
                if p_op < probs_dict[working_c]['DELETE']:
                    pass
                elif p_op < (probs_dict[working_c]['DELETE'] + probs_dict[working_c]['REPLACE']):
                    chars.append(get_op_char(rng, args, working_c, 'REPLACE', probs_dict, other_chars))
                else:
                    chars.append(get_op_char(rng, args, working_c, 'INSERT', probs_dict, other_chars))
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
    
    other_chars = set_other_chars(probs_dict)
    for c in other_chars:
        sys.stderr.write(c + "\n")
    
    for fn in args.jsonl:
        with open(fn) as f:
            for line in f:
                indata = json.loads(line)
                text = indata['text']
                noised = add_noise(text, rng, args, probs_dict, other_chars)
                outdata = { 'input': noised, 'output': text }
                print(json.dumps(outdata, ensure_ascii=False))
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))