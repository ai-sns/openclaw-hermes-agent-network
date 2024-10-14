# filename: find_chromedriver.py

import os

# List of common directories to search for ChromeDriver
common_directories = [
    'C:/Program Files/Google/Chrome/Application',
    'C:/Program Files (x86)/Google/Chrome/Application',
    os.path.expanduser('~')  # User home directory
]

# Function to search for chromedriver in given directories
def find_chromedriver():
    for directory in common_directories:
        for root, dirs, files in os.walk(directory):
            if 'chromedriver.exe' in files:
                return os.path.join(root, 'chromedriver.exe')
    return None

# Find ChromeDriver
chromedriver_path = find_chromedriver()

# Output the result
if chromedriver_path:
    print(f"ChromeDriver found at: {chromedriver_path}")
else:
    print("ChromeDriver not found in common directories. Please download it manually.")
