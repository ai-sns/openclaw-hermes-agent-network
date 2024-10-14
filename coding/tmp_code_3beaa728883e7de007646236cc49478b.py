import requests
from bs4 import BeautifulSoup

# Define the URL for Google News search for Trump
url = "https://news.google.com/search?q=Trump&hl=en-US&gl=US&ceid=US%3Aen"

# Perform the request to get the latest news about Trump
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('article')[:10]  # Get the first 10 articles
    news_list = []
    for article in articles:
        title = article.find('h3').get_text()
        link = article.find('a')['href']
        if not link.startswith('http'):
            link = 'https://news.google.com' + link  # Ensure the link is complete
        news_list.append(f"Title: {title}, URL: {link}")
    
    for news in news_list:
        print(news)
else:
    print(f"Error occurred: {response.status_code} - {response.text}")