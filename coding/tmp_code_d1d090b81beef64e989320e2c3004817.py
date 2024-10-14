from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time

class GetDatas:

    def __init__(self, company, DRIVER=None):
        self.company = company
        if DRIVER is None:
            self.DRIVER = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        else:
            self.DRIVER = DRIVER

    def webScraping(self):
        DRIVER = self.DRIVER
        DRIVER.get('https://www.google.com')
        time.sleep(2)  # Wait for the page to load
        search_box = DRIVER.find_element(By.NAME, 'q')
        search_box.send_keys(f'{self.company} news')
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)  # Wait for the results to load

        # Extracting news headlines
        headlines = DRIVER.find_elements(By.CSS_SELECTOR, 'h3')
        news = [headline.text for headline in headlines if headline.text]

        return news

# Usage
if __name__ == "__main__":
    scraper = GetDatas("Trump")
    news_articles = scraper.webScraping()
    for article in news_articles:
        print(article)