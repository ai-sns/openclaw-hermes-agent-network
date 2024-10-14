# filename: open_chrome_google.py

import webbrowser

# URL to open
url = 'https://www.google.com'

# Path to Chrome executable
chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'

# Register the browser
webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

# Open Chrome browser and navigate to the URL
webbrowser.get('chrome').open(url)