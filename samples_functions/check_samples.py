import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

from tqdm import tqdm
from argparse import ArgumentParser

def argparser():
    ap = ArgumentParser()
    ap.add_argument('--fixed-output', required=True)
    ap.add_argument('--unfixed-output', required=True)
    ap.add_argument('--correction', required=True)
    ap.add_argument('--graph', required=True)
    return ap

def get_dataframe(jsonl_file, cor_l):
    l = []
    group_len = 100
    with open(jsonl_file, 'rt', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            index = json_obj.get('index')
            if index not in cor_l:
                input_text = json_obj.get('input')
                output_text = json_obj.get('output')
                text_id = json_obj.get('text_id')
                chunk_id = json_obj.get('chunk_id')
                tokens = json_obj.get('tokens')
                l.append((index, input_text, output_text, len(output_text), 50+group_len*int((len(output_text)-50)/group_len), abs(len(input_text)-len(output_text)), text_id, chunk_id, tokens))
    columns = ['index', 'input', 'output', 'output_size', 's_output_size', 'len_diff', 'text_id', 'chunk_id', 'tokens']
    return pd.DataFrame(l, columns=columns)

def show_len_diff(df, graph):
    # for _, row in df_sorted.iterrows():
    #     print(row['index'], row['len_diff']/10, row['s_output_size'])
    # print(df)
    value_counts = df['s_output_size'].value_counts()
    sorted_counts = value_counts.sort_index()
    # for size, n in zip(sorted_counts.index.astype(str), sorted_counts.values):
    #     print(size, n)
    # print(list(sorted_counts.index.astype(str)))
    # print(list(sorted_counts.values))
    
    x_name = list(sorted_counts.index)
    x = [i/100 for i in x_name]
    x_name = [i-50 for i in x_name]
    y = list(sorted_counts.values)
    
    plt.bar(x, y, color ='orange', width = 0.8)

    plt.xlabel('Size')
    plt.ylabel('Number of texts')
    plt.title('Distribution of the size of the texts')
    
    plt.xticks(x, x_name, rotation=45)
    
    plt.savefig(graph)
    
def show_text(index, input_text, output_text):
    print("##############")
    print(f"INDEX: {index}; SIZE: {len(output_text)}")
    print(r"INPUT: {!r}".format(input_text))
    print(r"OUTPUT: {!r}".format(output_text))
    
def save_sample(jsonl_file, input_text, output_text, index, text_id, chunk_id, tokens):
    json_data = {
        "input": input_text,
        "output": output_text,
        "index": index,
        "text_id": text_id,
        "chunk_id": chunk_id,
        "output_size": len(output_text),
        "tokens": tokens
    }
    with open(jsonl_file, 'at', encoding='utf-8') as f:
        f.write(json.dumps(json_data) + '\n')

def show_texts(jsonl_file, df):
    pattern = r"\b\d+\b"
    for _, row in tqdm(df.iterrows(), total=len(df), desc='Samples done'):
        index = row['index']
        input_text = row['input']
        output_text = row['output']
        text_id = row['text_id']
        chunk_id = row['chunk_id']
        tokens = row['tokens']
        c = True
        liml, limr = -1, -1
        while c:
            show_text(index, input_text, output_text)
            res = input(" > Please enter the 2 numbers to cut the output text:\n\
   [2 digits to cut] - [1 digit (1) to save, (0) to exit] - [no digit to pass] -> ")
            matches = re.findall(pattern, res)
            if len(matches) >= 2:
                liml, limr = int(matches[0]), int(matches[1])
                print(liml, limr)
                output_text = cut_text(row['output'], liml, limr)
            elif len(matches) == 1:
                opt = int(matches[0])
                c = False
                if opt == 1:
                    print("Saving...")
                    save_sample(jsonl_file, input_text, output_text, index, text_id, chunk_id, tokens)
                elif opt == 0:
                    return
            else:
                c = False

def cut_text(text, liml, limr):
    if liml < 0:
        liml = 0
    if limr < 0:
        limr = 0
    if liml + limr >= len(text):
        return ""
    return text[liml:-limr] if limr > 0 else text[liml:]

def get_correction_indexes(jsonl_file):
    res = []
    with open(jsonl_file, 'rt') as f:
        for line in f:
            json_obj = json.loads(line)
            res.append(json_obj.get('index'))
    return res
    
def main(argv):
    args = argparser().parse_args()
    fixed_output = args.fixed_output
    unfixed_output = args.unfixed_output
    correction = args.correction
    graph = args.graph
    
    fixed_list = []
    unfixed_list = get_correction_indexes(correction)

    fixed_df = get_dataframe(fixed_output, fixed_list)
    unfixed_df = get_dataframe(unfixed_output, unfixed_list)
    
    # show_len_diff(fixed_df, graph)
    # print()
    # show_len_diff(unfixed_df.sort_values(by=['output_size'], ascending=False), graph)
    
    show_texts(correction, unfixed_df)
    
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))