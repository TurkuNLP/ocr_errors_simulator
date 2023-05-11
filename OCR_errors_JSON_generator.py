import Levenshtein as LV
import json
import pandas as pd
import csv
import sys
import os

from glob import glob
from tqdm import tqdm

import OCR_errors_JSON_generator_functions as ocr

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("-- Please use: python3 OCR_errors_JSON_generator.py input_directory output_jsonl charset_name")
    else:
        input_dir = sys.argv[1]
        jsonl_name = sys.argv[2]
        charset_name = sys.argv[3]
        
        json_content = {}
        
        csv_files = glob(os.path.join(input_dir, '*_converted.csv'))
        dataframe = pd.concat([pd.read_csv(file) for file in tqdm(csv_files, desc="Dataframe creation", unit=" files")])
        dataframe = dataframe.reset_index(drop=True)
        
        ocr.init_json_file(dataframe, json_content)
        
        with open(charset_name, 'r', encoding='utf-8') as charset:
            while (char := charset.read(1)):
                ocr.update_unknown_char(json_content, char, 1, 1)
        
        for index, row in tqdm(dataframe.iterrows(), total=len(dataframe), desc="Data processing   ", unit=" pairs"):
            ocr.add_data_to_json(row['input'], row['output'], json_content)
        
        with open(jsonl_name, 'w', encoding='utf-8') as json_file:
            json_file.write(json.dumps(json_content, indent=4))
        
        ocr.int_to_probabilities(jsonl_name)
        #ocr.print_low_count(jsonl_name)
        ocr.json2jsonl(jsonl_name, jsonl_name)