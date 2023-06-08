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
    ap.add_argument('--potential-samples', required=True)
    ap.add_argument('--final-samples', required=True)
    ap.add_argument('--p-graph', required=True)
    ap.add_argument('--f-graph', required=True)
    ap.add_argument('--precision', type=int, required=True)
    return ap

def get_label(n, p):
    return int(round(float(n) / (p)) * p)

def get_dataframe(jsonl_file, p):
    l = []
    with open(jsonl_file, 'rt', encoding='utf-8') as f:
        for line in f:
            json_obj = json.loads(line)
            index = json_obj.get('index')
            input_text = json_obj.get('input')
            output_text = json_obj.get('output')
            text_id = json_obj.get('text_id')
            chunk_id = json_obj.get('chunk_id')
            tokens = json_obj.get('tokens')
            l.append((index, input_text, output_text, len(output_text), get_label(len(output_text), p), abs(len(input_text)-len(output_text)), text_id, chunk_id, tokens))
    columns = ['index', 'input', 'output', 'output_size', 'label', 'len_diff', 'text_id', 'chunk_id', 'tokens']
    return pd.DataFrame(l, columns=columns)

def save_dataframe(jsonl_file, df):
    with open(jsonl_file, 'wt') as f:
        for _, row in df.iterrows():
            json_obj = {
                "input": row['input'],
                "output": row['output'],
                "index": row['index'],
                "text_id": row['text_id'],
                "chunk_id": row['chunk_id'],
                "output_size": len(row['output'])
            }
            f.write(json.dumps(json_obj) + '\n')

def create_graph(df, graph, p, color, marker):
    labels = np.sort(df['label'].unique())
    label_counts = df.groupby('label').size()
    x_values = list(labels)
    y_values = [label_counts.get(label, 0) for label in labels]
    print("labels:", list(labels))
    print("counts:", y_values)
    plt.bar(x_values, y_values, width=50.0, align='center', color=color, edgecolor=color)
    plt.ylim([0, 300])
    plt.savefig(graph)
    
def show_text(index, input_text, output_text):
    print("##############")
    print(f"INDEX: {index}; SIZE: {len(output_text)}")
    print(r"INPUT: {!r}".format(input_text))
    print(r"OUTPUT: {!r}".format(output_text))
    
def show_texts(df):
    for _, row in tqdm(df.iterrows(), total=len(df), desc='Samples'):
        index = row['index']
        input_text = row['input']
        output_text = row['output']
        text_id = row['text_id']
        chunk_id = row['chunk_id']
        tokens = row['tokens']
        show_text(index, input_text, output_text)
        res = input("Continue to display? ('n' to stop): ")
        if res == 'n':
            return
    
def filter_df(df):
    condition1 = ~df['output'].str.lower().str.contains("answer:")
    f_df = df.loc[condition1]
    # condition2 = df['output'].str.slice(stop=15).str.contains(":")
    # f_df = f_df.loc[condition2]
    return f_df

def main(argv):
    args = argparser().parse_args()
    potential_samples = args.potential_samples
    p_graph = args.p_graph
    f_graph = args.f_graph
    p = args.precision
    final_samples = args.final_samples
    p_df = get_dataframe(potential_samples, p)
    f_df = p_df[(p_df['output_size'] > 700) & (p_df['output_size'] < 1300)]
    f_df = filter_df(f_df)
    print(len(f_df), '/', len(p_df))
    
    sorted_df = f_df.sort_values(by='output_size', ascending=True)
    show_texts(sorted_df)
    sorted_df = f_df.sort_values(by='output_size', ascending=False)
    show_texts(sorted_df)
    
    create_graph(p_df, p_graph, p, 'red', 'o')
    create_graph(f_df, f_graph, p, 'green', 'x')
    save_dataframe(final_samples, f_df)
    
if __name__ == "__main__":
    sys.exit(main(sys.argv))