import requests

def fetch_latest_trump_news(api_key):
    url = f'https://newsapi.org/v2/everything?q=Trump&apiKey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
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
    else:
        return f"Error: {response.status_code}"

# Example usage (replace 'your_api_key' with a valid API key)
# print(fetch_latest_trump_news('your_api_key'))