# filename: fetch_ai_trends.py
import requests
from bs4 import BeautifulSoup

def fetch_ai_trends():
    url = "https://www.forbes.com/sites/bernardmarr/2023/01/09/the-top-5-ai-trends-in-2023/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    trends = []
    for item in soup.find_all('h3'):
        trends.append(item.get_text())

    return trends

if __name__ == "__main__":
    trends = fetch_ai_trends()
    print("Current AI Trends:")
    for trend in trends:
        print(f"- {trend}")

fetch_ai_trends()