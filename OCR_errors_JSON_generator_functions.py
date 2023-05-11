import Levenshtein as LV
import json
import csv
import os
import sys
import pandas as pd

def show_operators(ops, s1, s2):
    print("OPERATIONS:")
    for op,i1,i2 in ops:
        if op == 'insert':
            print("'\033[1m{}\033[0m' added before '\033[1m{}\033[0m'".format(s2[i2], s1[i1]))
        elif op == 'replace':
            print("'\033[1m{}\033[0m' replaced by '\033[1m{}\033[0m'".format(s2[i2], s1[i1]))
        else:
            print("'\033[1m{}\033[0m' deleted".format(s1[i1]))

def show_OCR_errors(s1, s2):
    ops = LV.editops(s1, s2)
    nbr_char = len(s1)
    nbr_ops = len(ops)
    nbr_keep = 0
    nbr_replace = 0
    nbr_insert = 0
    nbr_delete = 0
    
    shift = 0
    ops_index = 0
   
    for index in range(nbr_char):
        #print("{} - {} [{}]".format(index, s1[index], ops_index))
        if ops_index >= nbr_ops or ops[ops_index][1] != index:
            nbr_keep += 1
        else:
            if ops[ops_index][0] == 'insert':
                nbr_insert += 1
                shift += 1
            elif ops[ops_index][0] == 'replace':
                nbr_replace += 1
            else:
                nbr_delete +=1
                shift -=1
            ops_index += 1
    
    frq_keep = nbr_keep/nbr_char
    frq_insert = nbr_insert/nbr_ops
    frq_replace = nbr_replace/nbr_ops
    frq_delete = nbr_delete/nbr_ops
    
    print("CHARACTERS: {}".format(nbr_char))
    print("KEEP:       {} (\033[1m{}%\033[0m)".format(nbr_keep, frq_keep))
    print("Modifications (\033[1m{}%\033[0m):".format(1-frq_keep))
    print("  INSERT:     {} (\033[1m{}%\033[0m)".format(nbr_insert, frq_insert))
    print("  REPLACE:    {} (\033[1m{}%\033[0m)".format(nbr_replace, frq_replace))
    print("  DELETE:     {} (\033[1m{}%\033[0m)".format(nbr_delete, frq_delete))

def update_unknown_char(json_content, char, keep=0.0, count=0):
    if char not in json_content:
        json_content[char] = {
            "KEEP": keep,
            "DELETE": 0.0,
            "REPLACE": 0.0,
            "INSERT": 0.0,
            "REPLACE_CHAR": {},
            "INSERT_CHAR": {},
            "COUNT": count
        }
        return True
    return False

def init_json_file(dataframe, json_content):
    contents = ''.join(dataframe['output'])
    
    unique_chars = set(contents)
    
    update_unknown_char(json_content, 'OTHER_CHAR')
    
    for char in unique_chars:
        update_unknown_char(json_content, char)

def update_known_char(json_content, char, op, error=None):
    json_content[char]['COUNT'] += 1
    json_content[char][op] += 1
    json_content['OTHER_CHAR']['COUNT'] += 1
    json_content['OTHER_CHAR'][op] += 1
    
    if op == 'REPLACE':
        if error in json_content[char]['REPLACE_CHAR']:
            json_content[char]['REPLACE_CHAR'][error] += 1
        else:
            json_content[char]['REPLACE_CHAR'][error] = 1
        if error in json_content['OTHER_CHAR']['REPLACE_CHAR']:
            json_content['OTHER_CHAR']['REPLACE_CHAR'][error] += 1
        else:
            json_content['OTHER_CHAR']['REPLACE_CHAR'][error] = 1
            
    elif op == 'INSERT':
        if error in json_content[char]['INSERT_CHAR']:
            json_content[char]['INSERT_CHAR'][error] += 1
        else:
            json_content[char]['INSERT_CHAR'][error] = 1
        if error in json_content['OTHER_CHAR']['INSERT_CHAR']:
            json_content['OTHER_CHAR']['INSERT_CHAR'][error] += 1
        else:
            json_content['OTHER_CHAR']['INSERT_CHAR'][error] = 1

def char_section(char):
    if char != ' ':
        return char
    else:
        return ' ' # SPACE_CHAR

def add_data_to_json(noised_text, text, json_content):
    ops = LV.editops(text, noised_text)
    nbr_char = len(text)
    nbr_ops = len(ops)
    
    shift = 0
    ops_index = 0
   
    for index in range(nbr_char):
        if ops_index >= nbr_ops or ops[ops_index][1] != index:
            update_known_char(json_content, char_section(text[index]), 'KEEP')
        else:
            if ops[ops_index][0] == 'delete':
                update_known_char(json_content, char_section(text[index]), 'DELETE')
                shift -=1
            elif ops[ops_index][0] == 'replace':
                update_known_char(json_content, char_section(text[index]), 'REPLACE', char_section(noised_text[index+shift]))
            else:
                update_known_char(json_content, char_section(text[index]), 'INSERT', char_section(noised_text[index+shift]))
                shift += 1
            ops_index += 1

def add_all_data_to_json(csv_name, json_content):
    with open(csv_name, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        
        header = next(csv_reader)
        
        for row in csv_reader:
            add_data_to_json(row[0], row[1], json_content)

def int_to_probabilities(json_name):
    with open(json_name, 'r', encoding='utf-8') as json_file:
        json_content = json.load(json_file)
    
    for char in json_content:
        json_content[char]['KEEP'] /= json_content[char]['COUNT']
        nbr_modification = json_content[char]['DELETE']+json_content[char]['REPLACE']+json_content[char]['INSERT']

        if nbr_modification != 0:
            if json_content[char]['REPLACE'] != 0:
                for error in json_content[char]['REPLACE_CHAR']:
                    json_content[char]['REPLACE_CHAR'][error] /= json_content[char]['REPLACE']
            if json_content[char]['INSERT'] != 0:
                for error in json_content[char]['INSERT_CHAR']:
                    json_content[char]['INSERT_CHAR'][error] /= json_content[char]['INSERT']
        
            for op in ('DELETE', 'REPLACE', 'INSERT'):
                json_content[char][op] /= nbr_modification
    
    with open(json_name, 'w', encoding='utf-8') as json_file:
        json_object = json.dumps(json_content, indent=4)
        json_file.write(json_object)

def print_low_count(json_name):
    with open(json_name, 'r', encoding='utf-8') as json_file:
        json_content = json.load(json_file)
    
    nb = 0
    total = 0
    for char in json_content:
        count = json_content[char]['COUNT']
        if json_content[char]['KEEP'] == 1:
            sys.stderr.write(f"{char}")
            nb += 1
        total += 1
    sys.stderr.write(f"\n{nb}/{total}\n")
        
def json2jsonl(json_name, jsonl_name):
    with open(json_name, 'r', encoding='utf-8') as json_file:
        json_content = json.load(json_file)
    
    with open(jsonl_name, 'w', encoding='utf-8') as jsonl_file:
        for obj_name in json_content:
            obj = {obj_name: json_content[obj_name]}
            jsonl_file.write(json.dumps(obj) + '\n')