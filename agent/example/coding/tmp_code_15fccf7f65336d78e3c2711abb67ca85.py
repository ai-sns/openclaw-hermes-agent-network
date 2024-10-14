import requests
from bs4 import BeautifulSoup

def fetch_trump_news():
    url = "https://news.google.com/search?q=Trump%202024%20election&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    headlines = []
    for item in soup.find_all('h3'):
        headline = item.get_text()
        link = item.find('a')['href']
        headlines.append((headline, link))
    
    return headlines

news = fetch_trump_news()
for i, (headline, link) in enumerate(news, start=1):
    print(f"{i}. {headline}\n链接: {link}")