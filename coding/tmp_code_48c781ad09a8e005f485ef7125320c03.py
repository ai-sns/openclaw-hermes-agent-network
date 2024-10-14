import requests
from bs4 import BeautifulSoup

def fetch_latest_trump_news():
    url = 'https://www.bbc.co.uk/search?q=Trump'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        for item in soup.find_all('article'):
            title = item.find('h1') or item.find('h2')  # Adjust based on the site's structure
            description = item.find('p')
            link = item.find('a', href=True)
            if title and link:
                articles.append((title.get_text(strip=True), description.get_text(strip=True) if description else '', link['href']))
        
        return articles
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return []  # Return an empty list on error
    except Exception as err:
        print(f"An error occurred: {err}")
        return []  # Return an empty list on error

# Example usage
latest_news = fetch_latest_trump_news()
for news in latest_news:
    print(news)