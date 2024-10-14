import requests
from bs4 import BeautifulSoup

def fetch_weather_elements():
    url = "http://www.weather.com.cn/weather/101020100.shtml"  # 上海天气页面
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Print the relevant sections to identify the correct elements
        print("Temperature Section:")
        print(soup.find('p', class_='tem'))  # Print the temperature section
        
        print("\nWeather Condition Section:")
        print(soup.find('p', class_='wea'))  # Print the weather condition section
        
        print("\nHumidity Section:")
        print(soup.find('span', class_='shidu'))  # Print the humidity section
        
        print("\nWind Speed Section:")
        print(soup.find('p', class_='win'))  # Print the wind speed section
    else:
        print(f"Failed to retrieve data: {response.status_code}")

fetch_weather_elements()