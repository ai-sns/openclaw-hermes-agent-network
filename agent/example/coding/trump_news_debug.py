# filename: trump_news_debug.py
import requests
from bs4 import BeautifulSoup

def fetch_trump_news():
    url = "https://news.google.com/search?q=Trump%202024%20election&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(soup.prettify())  # 输出整个HTML内容以便调试

fetch_trump_news()