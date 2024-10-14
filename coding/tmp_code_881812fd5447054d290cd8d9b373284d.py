import requests

def get_latest_trump_news(api_key):
    url = f"https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        news_data = response.json()
        return news_data['articles']
    else:
        return f"Error: {response.status_code}"

# Example usage
api_key = 'YOUR_API_KEY'  # Replace with your actual API key
latest_news = get_latest_trump_news(api_key)
for article in latest_news:
    print(article['title'], article['url'])