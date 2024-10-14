import os
import datetime
import requests
from bs4 import BeautifulSoup
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

class getDatas:
    def __init__(self, company, DRIVER):
        self.company = company
        if DRIVER is None:
            self.DRIVER = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        else:
            self.DRIVER = DRIVER

    def webScraping(self):
        DRIVER = self.DRIVER
        DRIVER.get('https://www.google.com')
        DRIVER.find_element('xpath', '//*[@id="APjFqb"]').send_keys(f'{self.company} news', Keys.ENTER)
        headlines = []
        dates = []
        sources = []

        # Scraping news results
        articles = DRIVER.find_elements(By.TAG_NAME, 'article')
        for article in articles:
            try:
                headline = article.find_element(By.TAG_NAME, 'h3').text
                date = article.find_element(By.TAG_NAME, 'time').get_attribute('datetime')
                source = article.find_element(By.CLASS_NAME, 'wEwyrc').text
                headlines.append(headline)
                dates.append(date)
                sources.append(source)
            except Exception as e:
                print(f"Error extracting data from article: {e}")

        return headlines, dates, sources

class NewsHandle:
    def __init__(self):
        self.topics = ["Trump"]
        directory = os.path.join(os.getcwd(), "temp", "news")
        os.makedirs(directory, exist_ok=True)
        NOW = datetime.datetime.now()
        self.CSV = f'{directory}/news-{NOW.month}-{NOW.year}.csv'
        self.DRIVER = None  # Initialize DRIVER as None

    def run(self):
        headlines = []
        dates = []
        sources = []

        for topic in self.topics:
            try:
                data_fetcher = getDatas(topic, self.DRIVER)
                topic_headlines, topic_dates, topic_sources = data_fetcher.webScraping()
                headlines.extend(topic_headlines)
                dates.extend(topic_dates)
                sources.extend(topic_sources)
            except Exception as e:
                print(f"Error scraping news for {topic}: {e}")

        self.save_to_csv(headlines, dates, sources)

    def save_to_csv(self, headlines, dates, sources):
        with open(self.CSV, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Headline', 'Date', 'Source'])
            for headline, date, source in zip(headlines, dates, sources):
                writer.writerow([headline, date, source])

    def get_News(self):
        self.run()

# Execute the news scraping
news_handle = NewsHandle()
news_handle.get_News()
