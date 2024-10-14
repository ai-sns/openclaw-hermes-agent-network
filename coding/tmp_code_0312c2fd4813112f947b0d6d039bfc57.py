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
            title_tag = item.find('h3')
            source_tag = item.find('a', class_='wEwyrc')
            time_tag = item.find('time')

            title = title_tag.text if title_tag else 'Title not found'
            source = source_tag.text if source_tag else 'Source not found'
            publishedAt = time_tag['datetime'] if time_tag else 'Date not found'
            
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