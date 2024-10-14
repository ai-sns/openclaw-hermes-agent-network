# filename: open_chrome_selenium_manual.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# URL to open
url = 'https://www.google.com'

# Path to ChromeDriver executable
chromedriver_path = 'C:/Users/IDD/.wdm/drivers/chromedriver/win32/113.0.5672.63/chromedriver.exe'

# Setup Chrome options
chrome_options = webdriver.ChromeOptions()

# Initialize ChromeDriver
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the URL
driver.get(url)