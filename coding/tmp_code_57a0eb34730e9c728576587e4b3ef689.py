from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class GetDatas:

    def __init__(self, company, driver_path):
        self.company = company
        service = Service(driver_path)
        self.DRIVER = webdriver.Chrome(service=service)

    def webScraping(self):
        DRIVER = self.DRIVER
        DRIVER.get('https://www.google.com')
        
        # Use WebDriverWait instead of time.sleep
        try:
            search_box = WebDriverWait(DRIVER, 10).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            search_box.send_keys(f'{self.company} news')
            search_box.send_keys(Keys.ENTER)

            # Wait for the results to load
            WebDriverWait(DRIVER, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.cHaqb'))
            )

            # Extracting news headlines from the specified span class
            headlines = DRIVER.find_elements(By.CSS_SELECTOR, 'span.cHaqb')
            news = [headline.text for headline in headlines if headline.text]

            # Format into markdown table
            markdown_table = "| News Articles |\n|---------------|\n"
            for article in news:
                markdown_table += f"| {article} |\n"

        except Exception as e:
            print(f"An error occurred: {e}")
            markdown_table = "Error occurred during web scraping."

        finally:
            DRIVER.quit()  # Close the browser after scraping

        return markdown_table

# Usage
if __name__ == "__main__":
    driver_path = r"C:\Users\IDD\.wdm\drivers\chromedriver\win64\127.0.6533.99\chromedriver-win32\chromedriver.exe"
    scraper = GetDatas("Trump", driver_path)
    news_articles = scraper.webScraping()
    print(news_articles)