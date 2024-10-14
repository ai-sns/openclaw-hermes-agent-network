# filename: trump_news.py
import requests
from bs4 import BeautifulSoup

def fetch_trump_news():
    url = "https://news.google.com/search?q=Trump%202024%20election&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    headlines = []
    for item in soup.select('h3'):
        headline = item.get_text()
        link = "https://news.google.com" + item.find('a')['href'][1:]
        headlines.append((headline, link))
    
    return headlines

news = fetch_trump_news()
for i, (headline, link) in enumerate(news, start=1):
    print(f"{i}. {headline}\n链接: {link}")

# 获取新闻之后，翻译成中文
print("\n英文新闻翻译成中文：")
for headline, link in news:
    print(headline)

fetch_trump_news()