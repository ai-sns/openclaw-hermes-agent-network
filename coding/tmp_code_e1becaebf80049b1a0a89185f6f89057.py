import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def fetch_latest_trump_news():
    url = 'https://news.ycombinator.com/'  # Example website for news articles
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.find_all('tr', class_='athing'):
            title = item.find('a', class_='storylink')
            link = title['href']
            if title:
                articles.append((title.get_text(strip=True), link))
        
        return articles
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        return []  # Return an empty list on error
    except Exception as err:
        logging.error(f"An error occurred: {err}")
        return []  # Return an empty list on error

# Example usage
if __name__ == "__main__":
    latest_news = fetch_latest_trump_news()
    for news in latest_news:
        print(news)