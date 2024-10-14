import requests
from bs4 import BeautifulSoup

def fetch_trump_news():
    # 定义新闻来源
    sources = {
        "CNN": "https://www.cnn.com/search?q=Donald+Trump",
        "BBC": "https://www.bbc.co.uk/search?q=Donald+Trump"
    }
    
    news_articles = []

    for source, url in sources.items():
        try:
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 根据网站结构提取新闻标题和链接
            if source == "CNN":
                articles = soup.find_all('h3', class_='cnn-search__result-headline')
            elif source == "BBC":
                articles = soup.find_all('h1', class_='css-1aofmbn-PromoHeadline e1f5wbog0')
            else:
                continue  # 如果来源不在定义的列表中，跳过

            for article in articles:
                title = article.get_text()
                link = article.find('a')['href']
                if not link.startswith('http'):
                    link = f"https://{source.lower()}.com{link}"
                news_articles.append({"title": title, "link": link, "source": source})

        except requests.RequestException as e:
            print(f"Failed to fetch news from {source}: {e}")

    return news_articles

if __name__ == "__main__":
    trump_news = fetch_trump_news()
    for news in trump_news:
        print(f"{news['source']}: {news['title']} - {news['link']}")