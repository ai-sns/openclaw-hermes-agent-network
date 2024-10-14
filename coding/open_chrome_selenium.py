# filename: open_chrome_selenium.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# URL to open
url = 'https://www.google.com'

# Setup Chrome options
chrome_options = webdriver.ChromeOptions()

# Initialize ChromeDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the URL
driver.get(url)