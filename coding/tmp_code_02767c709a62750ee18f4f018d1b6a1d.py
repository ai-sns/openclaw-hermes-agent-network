import requests

def fetch_latest_trump_news(api_key):
    url = f'https://newsapi.org/v2/everything?q=Trump&sortBy=publishedAt&apiKey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        news_data = response.json()
        articles = news_data.get('articles', [])
        return articles
    else:
        print(f"Error fetching news: {response.status_code}")
        return None

# Example usage
if __name__ == "__main__":
    api_key = 'YOUR_API_KEY'  # Replace with your actual API key
    latest_news = fetch_latest_trump_news(api_key)
    if latest_news:
        for article in latest_news:
            print(f"Title: {article['title']}\nDescription: {article['description']}\nURL: {article['url']}\n")
    else:
        print("No news articles found.")