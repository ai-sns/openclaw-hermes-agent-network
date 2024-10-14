import requests
from bs4 import BeautifulSoup

# Define the URL for CNN search for Trump
url = "https://www.cnn.com/search?size=10&q=Trump"

# Perform the request to get the latest news about Trump
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('h3', class_='cnn-search__result-headline')[:10]  # Get the first 10 articles
    news_list = []
    for article in articles:
        title = article.get_text()
        link = article.find('a')['href']
        if not link.startswith('http'):
            link = 'https://www.cnn.com' + link  # Ensure the link is complete
        news_list.append(f"Title: {title}, URL: {link}")
    
    for news in news_list:
        print(news)
else:
    print(f"Error occurred: {response.status_code} - {response.text}")