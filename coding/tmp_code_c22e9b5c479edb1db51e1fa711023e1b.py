import requests
import os
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_latest_trump_news():
    """
    Fetch the latest news articles related to Trump from NewsAPI.
    
    Returns:
        list: A list of news articles or a message indicating no articles found.
    """
    api_key = os.getenv('NEWS_API_KEY')  # Fetch API key from environment variable
    url = f'https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        news_data = response.json()
        if news_data['totalResults'] > 0:
            return news_data['articles']
        else:
            return {"message": "No news articles found."}
    else:
        return {"error": f"Failed to fetch news: {response.status_code}"}

# Example usage
latest_news = fetch_latest_trump_news()
print(latest_news)