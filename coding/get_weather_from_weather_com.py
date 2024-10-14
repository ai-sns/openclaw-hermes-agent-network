# filename: get_weather_from_weather_com.py
import requests
from bs4 import BeautifulSoup

def get_weather():
    url = "https://www.weather.com/zh-CN/weather/tomorrow/l/CHXX0008:1:CH"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取今日和明天的天气信息
    today_weather = soup.find('div', class_='CurrentConditions--phraseValue--2xXSr').text
    tomorrow_weather = soup.find_all('span', class_='DailyContent--temp--_8DL5')[1].text

    return today_weather, tomorrow_weather

today_weather, tomorrow_weather = get_weather()
print(f"上海今天的天气: {today_weather}")
print(f"上海明天的天气: {tomorrow_weather}")