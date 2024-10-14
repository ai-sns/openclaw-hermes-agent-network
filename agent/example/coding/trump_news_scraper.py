# filename: trump_news_scraper.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import time

def fetch_trump_news():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 如果需要后台运行，保持这一行

    # 使用绝对路径确保能够找到chromedriver.exe
    driver_path = 'C:\\chromedriver\\chromedriver.exe'  # 保证使用反斜杠或者直接使用单斜杠
    print(f"Using chromedriver from: {driver_path}")
    print(f"File exists: {os.path.exists(driver_path)}")  # 检查文件是否存在

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://news.google.com")
        search_box = driver.find_element(By.NAME, 'q')
        search_box.send_keys("Trump 2024 election")
        search_box.submit()

        time.sleep(3)  # 等待页面加载

        headlines = driver.find_elements(By.TAG_NAME, 'h3')
        for i, headline in enumerate(headlines, start=1):
            print(f"{i}. {headline.text}")
    finally:
        driver.quit()

fetch_trump_news()