import requests

def fetch_latest_trump_news(api_key):
    """
    Fetch the latest news articles related to Trump from the News API.
    
    Parameters:
    api_key (str): Your API key for authentication.
    
    Returns:
    list: A list of news articles with title, description, and URL.
    """
    url = f'https://newsapi.org/v2/everything?q=Trump&apiKey={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        
        news_data = response.json()
        articles = news_data.get('articles', [])
        latest_news = []
        
        for article in articles:
            news_item = {
                'title': article['title'],
                'description': article['description'],
                'url': article['url']
            }
            latest_news.append(news_item)
        
        return latest_news
    
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

# Example usage (replace 'your_api_key' with a valid API key)
# print(fetch_latest_trump_news('your_api_key'))