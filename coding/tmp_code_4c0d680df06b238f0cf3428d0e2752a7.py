import requests
from bs4 import BeautifulSoup

def fetch_latest_trump_news():
    url = 'https://news.google.com/search?q=Trump&hl=en-US&gl=US&ceid=US%3Aen'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.find_all('article'):
            title = item.find('h3').text if item.find('h3') else 'No title'
            source = item.find('a', class_='wEwyrc').text if item.find('a', class_='wEwyrc') else 'No source'
            publishedAt = item.find('time')['datetime'] if item.find('time') else 'No date'
            articles.append({
                'title': title,
                'source': source,
                'publishedAt': publishedAt
            })
        
        return articles
    except Exception as e:
        return f"An error occurred: {e}"

# Example usage
latest_news = fetch_latest_trump_news()
print(latest_news)