import requests
from bs4 import BeautifulSoup

# Define the URL for a news website that covers Trump news
url = "https://www.bbc.com/news/topics/cyxr8w3j0vvt/trump"

# Perform the request to get the latest news about Trump
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('h3', class_='gs-c-promo-heading__title')[:10]  # Get the first 10 articles
    for article in articles:
        title = article.get_text()
        link = article.find_parent('a')['href']
        if not link.startswith('http'):
            link = 'https://www.bbc.com' + link  # Ensure the link is complete
        print(f"Title: {title}, URL: {link}")
else:
    print(f"Error occurred: {response.status_code} - {response.text}")