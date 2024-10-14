# filename: open_chrome_google_subprocess.py

import subprocess
import os

# URL to open
url = 'https://www.google.com'

# Path to Chrome executable
chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

# Check if the chrome executable exists
if not os.path.isfile(chrome_path):
    raise FileNotFoundError(f"Chrome executable not found at {chrome_path}")

# Open Chrome browser and navigate to the URL
subprocess.run([chrome_path, url])