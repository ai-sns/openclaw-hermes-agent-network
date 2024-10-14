import feedparser

def fetch_latest_trump_news():
    # Example RSS feed URL for news related to Trump
    rss_url = "https://news.google.com/rss/search?q=Trump&hl=en-US&gl=US&ceid=US:en"
    
    news_feed = feedparser.parse(rss_url)
    latest_news = []
    
    for entry in news_feed.entries:
        title = entry.title
        published_at = entry.published
        link = entry.link
        latest_news.append({'title': title, 'published_at': published_at, 'link': link})
    
    return latest_news

# Example usage
# print(fetch_latest_trump_news())