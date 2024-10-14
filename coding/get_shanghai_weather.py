# filename: get_shanghai_weather.py
import requests
from bs4 import BeautifulSoup

def get_shanghai_weather():
    url = "https://www.timeanddate.com/weather/china/shanghai"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Print the entire page HTML for inspection
        print(soup.prettify())
    
    else:
        print(f"Failed to access the website. HTTP Status code: {response.status_code}")

# Execute the function to get and print the page HTML content
get_shanghai_weather()