import requests
from bs4 import BeautifulSoup

def fetch_latest_trump_news():
    url = 'https://www.bbc.com/news'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an error for bad responses
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('h3')  # BBC uses <h3> for headlines
        trump_news = []
        
        for article in articles:
            title = article.get_text()
            link = article.find('a')['href']
            
            # Handle relative URLs
            if link.startswith('/'):
                link = 'https://www.bbc.com' + link
            
            # Case-insensitive check for "Trump"
            if 'trump' in title.lower():
                trump_news.append({'title': title, 'url': link})
        
        return trump_news
    else:
        return None

# Example usage
latest_news = fetch_latest_trump_news()
if latest_news:
    for article in latest_news:
        print(f"Title: {article['title']}\nURL: {article['url']}\n{'-'*40}")
else:
    print("No news articles found.")