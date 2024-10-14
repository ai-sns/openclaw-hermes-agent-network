import os
import requests
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

def fetch_latest_trump_news(api_key):
    url = f'https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        if articles:
            for article in articles:
                title = article.get('title', 'No title available')
                url = article.get('url', 'No URL available')
                source = article.get('source', {}).get('name', 'Unknown source')
                published_at = article.get('publishedAt', 'No publication date available')
                
                print(f"Title: {title}")
                print(f"Source: {source}")
                print(f"Published At: {published_at}")
                print(f"URL: {url}\n")
        else:
            print("No articles found.")
    else:
        print(f"Failed to fetch news articles. Status code: {response.status_code}")

# Ensure to set your API key in a .env file as 'API_KEY'
fetch_latest_trump_news(os.getenv('API_KEY'))