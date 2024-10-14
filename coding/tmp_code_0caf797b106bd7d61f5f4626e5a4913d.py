import os
import requests

def fetch_latest_trump_news():
    """
    Fetch the latest news articles related to Trump from the NewsAPI.

    Returns:
        list: A list of tuples containing the title, description, URL, and publication date of each article.
               Returns an empty list if an error occurs.
    """
    api_key = os.getenv('NEWS_API_KEY')  # Use environment variable for API key
    url = f'https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        news_data = response.json()
        articles = news_data.get('articles', [])
        return [(article['title'], article['description'], article['url'], article['publishedAt']) for article in articles]
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return []  # Return an empty list on error
    except Exception as err:
        print(f"An error occurred: {err}")
        return []  # Return an empty list on error

# Example usage
# Ensure to set the environment variable before running
# latest_news = fetch_latest_trump_news()
# print(latest_news)