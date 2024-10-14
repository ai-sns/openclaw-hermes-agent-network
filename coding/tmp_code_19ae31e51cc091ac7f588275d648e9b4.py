import requests

def fetch_latest_trump_news(api_key):
    url = f"https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                'title': article['title'],
                'publishedAt': article['publishedAt'],
                'description': article['description']
            })
        return formatted_articles
    else:
        return f"Error: {response.status_code}"

# Example usage (replace 'your_api_key' with a valid API key)
# news_articles = fetch_latest_trump_news('your_api_key')
# print(news_articles)