from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

def fetch_trump_news():
    # Define news sources
    sources = {
        "CNN": "https://www.cnn.com/search?q=Donald+Trump",
        "BBC": "https://www.bbc.co.uk/search?q=Donald+Trump"
    }
    
    news_articles = []

    # Set up Selenium WebDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    for source, url in sources.items():
        try:
            driver.get(url)
            time.sleep(5)  # Wait for the page to load

            # Extract news titles and links based on website structure
            if source == "CNN":
                articles = driver.find_elements(By.CSS_SELECTOR, 'h3.cnn-search__result-headline')
            elif source == "BBC":
                articles = driver.find_elements(By.CSS_SELECTOR, 'h1.css-1aofmbn-PromoHeadline.e1f5wbog0')
            else:
                continue  # Skip if the source is not in the defined list

            for article in articles:
                title = article.text
                link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
                news_articles.append({"title": title, "link": link, "source": source})

        except Exception as e:
            print(f"Failed to fetch news from {source}: {e}")

    driver.quit()  # Close the browser
    return news_articles

if __name__ == "__main__":
    trump_news = fetch_trump_news()
    for news in trump_news:
        print(f"{news['source']}: {news['title']} - {news['link']}")