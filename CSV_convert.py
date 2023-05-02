import os
import csv
import sys
import re

def preprocessing_text(text):
    text[0] = re.sub('[\n\t]', ' ', text[0])
    text[0] = text[0].strip()
    text[0] = re.sub(' +', ' ', text[0])
    return text

def convert_csv(csv_dir, output_dir):
    total_files = len([file_name for file_name in os.listdir(csv_dir) if file_name.endswith('.csv')])
    completed_files = 0
    for file_name in os.listdir(csv_dir):
        if file_name.endswith('.csv'):
            input_csv_path = os.path.join(csv_dir, file_name)
            good_csv_path = os.path.join(output_dir, file_name.replace('.csv', '_good.csv'))
            error_csv_path = os.path.join(output_dir, file_name.replace('.csv', '_error.csv'))
            
            try:
                with open(input_csv_path, 'r', encoding='utf-8') as input_csv, open(good_csv_path, 'w', encoding='utf-8') as good_csv, open(error_csv_path, 'w', encoding='utf-8') as error_csv:
                    reader = csv.reader(input_csv)
                    header = next(reader)
                    good_writer = csv.writer(good_csv)
                    error_writer = csv.writer(error_csv)
                    
                    good_writer.writerow(['good_texts'])
                    error_writer.writerow(['error_texts'])
        
                    for row in reader:
                        good_writer.writerow(preprocessing_text([row[2]]))
                        error_writer.writerow(preprocessing_text([row[1]]))
                
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