import requests
import os

def get_latest_trump_news(api_key):
    url = f"https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        news_data = response.json()
        
        # Check if 'articles' is in the response and is a list
        if 'articles' in news_data and isinstance(news_data['articles'], list):
            return news_data['articles']
        else:
            return []  # Return an empty list if no articles found
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

# Example usage
api_key = os.getenv('NEWS_API_KEY')  # Use environment variable for API key
latest_news = get_latest_trump_news(api_key)
if latest_news:
    for article in latest_news:
        # Ensure article is a dictionary and has the expected keys
        if isinstance(article, dict) and 'title' in article and 'url' in article:
            print(article['title'], article['url'])
else:
    print("No articles found or an error occurred.")