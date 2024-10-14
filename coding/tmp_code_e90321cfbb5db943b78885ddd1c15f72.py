from RPACommon import *
import os
import datetime

class NewsHandle:
    def __init__(self):
        self.topics = []
        self.DRIVER = getDatas('', None).DRIVER
        directory = os.path.join(Path(__file__).resolve().parent, "temp", "news")
        NOW = datetime.datetime.now()
        self.CSV = f'{directory}-{NOW.month}-{NOW.year}.csv'
    
    def run(self):
        headlines = []
        dates = []
        sources = []

        for topic in self.topics:
            headline, date, source = getDatas(topic, self.DRIVER).webScrapingNews()  # Updated method for news scraping
            headlines.append(headline)
            dates.append(date)
            sources.append(source)

        self.DRIVER.close()
        sheets(headlines, dates, sources).importSheet()  # Save news data in CSV format

    def get_News(self, topics):
        self.topics = topics

        while True:
            try:
                backup(self.CSV).save()  # Backup the CSV file
                self.run()
                self.DRIVER.close()
            except:
                print(f"Already there's the file: {self.CSV}")
                break