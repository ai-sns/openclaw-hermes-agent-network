import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GetDatas:

    def __init__(self, company, driver_path, wait_time=10):
        self.company = company
        self.wait_time = wait_time
        service = Service(driver_path)
        self.DRIVER = webdriver.Chrome(service=service)

    def webScraping(self):
        DRIVER = self.DRIVER
        DRIVER.get('https://www.google.com')
        
        try:
            search_box = WebDriverWait(DRIVER, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            search_box.send_keys(f'{self.company} news')
            search_box.send_keys(Keys.ENTER)

            # Wait for the results to load
            WebDriverWait(DRIVER, self.wait_time).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.cHaqb'))
            )

            # Extracting news headlines and URLs
            articles = DRIVER.find_elements(By.CSS_SELECTOR, 'span.cHaqb')
            news = []
            for article in articles:
                if article.text:
                    try:
                        # Find the closest anchor tag that contains the link
                        parent_link = article.find_element(By.XPATH, './ancestor::a')
                        url = parent_link.get_attribute('href')
                        news.append((article.text, url))
                    except Exception as e:
                        logging.warning(f"Could not find URL for article: {article.text}. Error: {e}")

            # Format into markdown table
            markdown_table = "| News Articles | URL |\n|---------------|-----|\n"
            for article, url in news:
                markdown_table += f"| {article} | [Link]({url}) |\n"

        except Exception as e:
            logging.error(f"An error occurred: {e}")
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