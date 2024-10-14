from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fetch_latest_trump_news():
    # Specify the path to the manually installed ChromeDriver
    chrome_driver_path = r'C:\Users\IDD\.wdm\drivers\chromedriver\win64\127.0.6533.99\chromedriver-win32\chromedriver.exe'  # Updated path
    driver = webdriver.Chrome(service=Service(chrome_driver_path))
    driver.get('https://www.bbc.com/news')
    
    # Wait for the page to load and for the articles to be present
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'h3')))
    except Exception as e:
        print(f"An error occurred while waiting for the page to load: {e}")
    
    # Debugging output: print the first 1000 characters of the HTML
    print(driver.page_source[:1000])  # This will help us see the structure
    
    # Find articles
    articles = driver.find_elements(By.TAG_NAME, 'h3')
    trump_news = []
    
    for article in articles:
        title = article.text
        link = article.find_element(By.TAG_NAME, 'a').get_attribute('href') if article.find_elements(By.TAG_NAME, 'a') else None
        
        # Case-insensitive check for "Trump"
        if link and 'trump' in title.lower():
            trump_news.append({'title': title, 'url': link})
    
    driver.quit()  # Close the browser
    return trump_news

# Example usage
latest_news = fetch_latest_trump_news()
if latest_news:
    for article in latest_news:
        print(f"Title: {article['title']}\nURL: {article['url']}\n{'-'*40}")
else:
    print("No news articles found.")