import requests
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(level=logging.INFO)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_latest_news(query='Trump'):
    """
    Fetch the latest news articles related to a specified query from NewsAPI.
    
    Args:
        query (str): The search term for news articles. Default is 'Trump'.
    
    Returns:
        list: A list of news articles or a message indicating no articles found.
    """
    api_key = os.getenv('NEWS_API_KEY')  # Fetch API key from environment variable
    if not api_key:
        logging.error("API key not found. Please set the NEWS_API_KEY environment variable.")
        return {"error": "API key not found."}
    
    url = f'https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        news_data = response.json()
        if news_data['totalResults'] > 0:
            return news_data['articles']
        else:
            return {"message": "No news articles found."}
    else:
        logging.error(f"Failed to fetch news: {response.status_code}")
        return {"error": f"Failed to fetch news: {response.status_code}"}

# Example usage
if __name__ == "__main__":
    latest_news = fetch_latest_news()
    if isinstance(latest_news, list):
        for article in latest_news:
            print(f"Title: {article['title']}")
            print(f"Description: {article['description']}")
            print(f"URL: {article['url']}\n")
    else:
        print(latest_news)