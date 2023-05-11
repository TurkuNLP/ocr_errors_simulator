# ocr_errors_simulator
Functions and codes used to determine probabilities on OCR errors and simulate them

For the charset, use JSONL_reading.py to preprocess the ecco file (creation of different files to create chunks of the compressed data). Then, use charset.py to create the charset that will be in a file text.
For the JSONL file for probabilities, use CSV_convert.py to preprocess the CSV files to fit with the following Python file, OCR_errors_JSON_generator.py.
If everything has been done correctly, use OCR_noise.py to create OCR noise.
