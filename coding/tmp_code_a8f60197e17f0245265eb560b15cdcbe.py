import requests
from bs4 import BeautifulSoup

def fetch_latest_trump_news():
    url = "https://news.google.com/search?q=Trump&hl=en-US&gl=US&ceid=US%3Aen"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article')
        formatted_articles = []
        
        for article in articles:
            title_tag = article.find('h3')
            title = title_tag.text if title_tag else 'No title'
            link_tag = article.find('a')
            link = link_tag['href'] if link_tag else 'No link'
            description_tag = article.find('span')
            description = description_tag.text if description_tag else 'No description'
            formatted_articles.append({
                'title': title,
                'link': f"https://news.google.com{link[1:]}",  # Adjust link to be absolute
                'description': description
            })
        
        return formatted_articles
    else:
        return f"Error: {response.status_code}"

# Fetch and print the latest news articles about Trump
news_articles = fetch_latest_trump_news()
print(news_articles)