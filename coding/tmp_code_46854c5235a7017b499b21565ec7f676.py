import requests
from bs4 import BeautifulSoup

def search_github(query):
    url = f"https://github.com/search?q={query}"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('a', class_='v-align-middle')
        
        urls = []
        for result in results:
            href = result.get('href')
            if href:
                urls.append(f"https://github.com{href}")
        
        return urls
    else:
        print("Error fetching the URL")
        return []

if __name__ == "__main__":
    query = "autogen"
    urls = search_github(query)
    
    if urls:
        print("Found URLs:")
        for url in urls:
            print(url)
    else:
        print("No URLs found.")