from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fetch_latest_trump_news():
    chrome_driver_path = r'C:\Users\IDD\.wdm\drivers\chromedriver\win64\127.0.6533.99\chromedriver-win32\chromedriver.exe'
    driver = webdriver.Chrome(service=Service(chrome_driver_path))
    driver.get('https://news.google.com/search?q=Trump')

    # Wait for the page to load and for the articles to be present
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article')))
    except Exception as e:
        print(f"An error occurred while waiting for the page to load: {e}")

    # Find articles
    articles = driver.find_elements(By.CSS_SELECTOR, 'article')
    trump_news = []

    for article in articles:
        try:
            # Use a more general selector to find the title
            title_element = article.find_element(By.CSS_SELECTOR, 'h3, h4')  # Adjusted to include h4 as well
            title = title_element.text
            link = title_element.find_element(By.TAG_NAME, 'a').get_attribute('href') if title_element.find_elements(By.TAG_NAME, 'a') else None
            
            # Case-insensitive check for "Trump"
            if link and 'trump' in title.lower():
                trump_news.append({'title': title, 'url': link})
        except Exception as e:
            print(f"An error occurred while processing an article: {e}")

    driver.quit()  # Close the browser
    return trump_news

# Example usage
latest_news = fetch_latest_trump_news()
if latest_news:
    for article in latest_news:
        print(f"Title: {article['title']}\nURL: {article['url']}\n{'-'*40}")
else:
    print("No news articles found.")