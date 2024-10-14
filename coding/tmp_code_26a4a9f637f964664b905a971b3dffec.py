import requests
import os

def fetch_latest_news(api_key):
    """
    Fetch the latest news articles related to Trump.

    Parameters:
    api_key (str): The API key for authenticating with the NewsAPI.

    Returns:
    dict: A dictionary containing the news articles or an error message.
    """
    url = f'https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {'error': f'HTTP error occurred: {http_err}'}
    except Exception as err:
        return {'error': f'An error occurred: {err}'}

# Example usage
if __name__ == "__main__":
    API_KEY = os.getenv('NEWS_API_KEY')  # Use environment variable for API key
    if not API_KEY:
        print("Error: API key is not set. Please set the NEWS_API_KEY environment variable.")
    else:
        news_data = fetch_latest_news(API_KEY)
        print(news_data)