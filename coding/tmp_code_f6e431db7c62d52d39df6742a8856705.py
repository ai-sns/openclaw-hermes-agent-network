from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time

def fetch_latest_trump_news():
    # Specify the path to the manually installed ChromeDriver
    chrome_driver_path = r'C:\Users\IDD\.wdm\drivers\chromedriver\win64\127.0.6533.72\chromedriver-win32.exe'  # Updated path
    driver = webdriver.Chrome(service=Service(chrome_driver_path))
    driver.get('https://www.bbc.com/news')
    
    # Allow time for the page to load
    time.sleep(5)  # Adjust sleep time as necessary
    
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