import Levenshtein as LV
import json
import csv
import sys
import os

import OCR_errors_JSON_generator_functions as ocr

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("-- Please use: python3 OCR_errors_JSON_generator.py input_directory output_jsonl")
    else:
        input_dir = sys.argv[1]
        jsonl_name = sys.argv[2]
        total_pairs = len([file_name for file_name in os.listdir(input_dir) if file_name.endswith('_good.csv')])
        completed_pairs_init = 0
        completed_pairs_jsonl = 0
        
        for file_name in os.listdir(input_dir):
            if file_name.endswith('_good.csv'):
                good_csv_name = os.path.join(input_dir, file_name)
                if completed_pairs_init == 0:
                    ocr.init_json_file(good_csv_name, jsonl_name)
                else:
                    ocr.init_json_file(good_csv_name, jsonl_name, True)
                completed_pairs_init += 1
                percentage = 100*completed_pairs_init/total_pairs
                print(f"Completed pairs {completed_pairs_init}/{total_pairs} ({percentage:.1f}%)")
        
        for file_name in os.listdir(input_dir):
            if file_name.endswith('_good.csv'):
                good_csv_name = os.path.join(input_dir, file_name)
                error_csv_name = os.path.join(input_dir, file_name.replace('_good.csv', '_error.csv'))
                ocr.add_all_data_to_json(good_csv_name, error_csv_name, jsonl_name)
                completed_pairs_jsonl += 1
                percentage = 100*completed_pairs_jsonl/total_pairs
                print(f"Completed pairs {completed_pairs_jsonl}/{total_pairs} ({percentage:.1f}%)")
        
        ocr.int_to_probabilities(jsonl_name)
        ocr.json2jsonl(jsonl_name, jsonl_name)