import os
import datetime
import requests
from bs4 import BeautifulSoup
import csv

class NewsHandle:
    def __init__(self):
        self.topics = ["Trump"]
        directory = os.path.join(os.getcwd(), "temp", "news")
        os.makedirs(directory, exist_ok=True)
        NOW = datetime.datetime.now()
        self.CSV = f'{directory}/news-{NOW.month}-{NOW.year}.csv'

    def run(self):
        headlines = []
        dates = []
        sources = []

        for topic in self.topics:
            try:
                self.scrape_news_data(topic, headlines, dates, sources)
            except Exception as e:
                print(f"Error scraping news for {topic}: {e}")

        self.save_to_csv(headlines, dates, sources)

    def scrape_news_data(self, topic, headlines, dates, sources):
        url = f"https://news.google.com/search?q={topic}&hl=en-US&gl=US&ceid=US:en"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        for item in soup.find_all('article'):
            headline = item.find('h3').text if item.find('h3') else 'No headline'
            date = item.find('time')['datetime'] if item.find('time') else 'No date'
            source = item.find('a', class_='wEwyrc').text if item.find('a', class_='wEwyrc') else 'No source'
            headlines.append(headline)
            dates.append(date)
            sources.append(source)

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