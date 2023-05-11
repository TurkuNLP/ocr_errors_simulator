import os
import csv
import sys
import re
import unicodedata

def preprocessing_text(text):
    text = re.sub('[\n\t]', ' ', text)
    text = text.strip()
    text = re.sub(' +', ' ', text)
    text = ''.join(c for c in text if unicodedata.category(c) == 'Zs' or c.isprintable())
    return text

def convert_csv(csv_dir, output_dir):
    total_files = len([file_name for file_name in os.listdir(csv_dir) if file_name.endswith('.csv')])
    completed_files = 0
    for file_name in os.listdir(csv_dir):
        if file_name.endswith('.csv'):
            input_csv_path = os.path.join(csv_dir, file_name)
            output_csv_path = os.path.join(output_dir, file_name.replace('.csv', '_converted.csv'))
            
            try:
                with open(input_csv_path, 'r', encoding='utf-8') as input_csv, open(output_csv_path, 'w', encoding='utf-8') as output_csv:
                    reader = csv.reader(input_csv)
                    header = next(reader)
                    output_writer = csv.writer(output_csv)
                    
                    output_writer.writerow(['input', 'output'])
        
                    for row in reader:
                        output_writer.writerow([preprocessing_text(row[1]), preprocessing_text(row[2])])
                
                completed_files += 1
                progress_percentage = (completed_files / total_files) * 100
                print(f"Progress: {completed_files}/{total_files} files ({progress_percentage:.1f}%)")
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("-- Please use: python3 CSV_convert.py input_directory output_directory")
    else:
        csv_dir = sys.argv[1]
        output_dir = sys.argv[2]
        convert_csv(csv_dir, output_dir)