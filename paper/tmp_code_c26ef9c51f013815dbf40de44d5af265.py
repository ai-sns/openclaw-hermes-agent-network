import requests
from bs4 import BeautifulSoup

def search_github(query):
    url = f"https://github.com/search?q={query}"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('a', class_='v-align-middle')
        
        for result in results:
            print(f"Title: {result.text.strip()}")
            print(f"URL: https://github.com{result['href']}")
            print()
    else:
        print("Failed to retrieve results")

search_github("autogen")