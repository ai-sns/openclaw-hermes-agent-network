# filename: get_weather_no_key.py
import requests
from bs4 import BeautifulSoup

def get_weather(city):
    url = f"https://www.weather.com/en-IN/weather/today/l/{city}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    weather = soup.find('span', class_='CurrentConditions--tempValue--3a50n').text
    description = soup.find('div', class_='CurrentConditions--phraseValue--2xXSr').text
    return f"Current temperature: {weather}, Description: {description}"

if __name__ == "__main__":
    city = "China:SH"  # Using the code for Shanghai
    weather_info = get_weather(city)
    print(weather_info)