# filename: analyze_csv.py
import pandas as pd

# File path
file_path = r'C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv'

# Read the CSV file
data = pd.read_csv(file_path)

# Analyze and print the results
print(f"Number of rows: {data.shape[0]}")
print(f"Number of columns: {data.shape[1]}")
print("First few rows of the data:")
print(data.head())