from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class GetDatas:

    def __init__(self, company, driver_path):
        self.company = company
        self.DRIVER = webdriver.Chrome(executable_path=driver_path)

    def webScraping(self):
        DRIVER = self.DRIVER
        DRIVER.get('https://www.google.com')
        time.sleep(2)  # Wait for the page to load
        search_box = DRIVER.find_element(By.NAME, 'q')
        search_box.send_keys(f'{self.company} news')
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)  # Wait for the results to load

        # Extracting news headlines from the specified span class
        headlines = DRIVER.find_elements(By.CSS_SELECTOR, 'span.cHaqb')
        news = [headline.text for headline in headlines if headline.text]

        # Format into markdown table
        markdown_table = "| News Articles |\n|---------------|\n"
        for article in news:
            markdown_table += f"| {article} |\n"

        DRIVER.quit()  # Close the browser after scraping
        return markdown_table

# Usage
if __name__ == "__main__":
    driver_path = r"C:\Users\IDD\.wdm\drivers\chromedriver\win64\127.0.6533.99\chromedriver-win32\chromedriver.exe"
    scraper = GetDatas("Trump", driver_path)
    news_articles = scraper.webScraping()
    print(news_articles)