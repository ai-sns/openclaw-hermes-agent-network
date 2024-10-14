# filename: get_weather_from_weather_com_v2.py
import requests
from bs4 import BeautifulSoup

def get_weather():
    url = "https://www.weather.com/zh-CN/weather/tomorrow/l/CHXX0008:1:CH"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 提取今日天气（如果存在）
    today_weather = soup.find('div', class_='CurrentConditions--phraseValue--2xXSr')
    today_weather_text = today_weather.text if today_weather else "天气信息未找到"

    # 提取明天的天气
    tomorrow_weather = soup.find_all('span', class_='DailyContent--temp--_8DL5')
    tomorrow_weather_text = tomorrow_weather[1].text if len(tomorrow_weather) > 1 else "天气信息未找到"

    return today_weather_text, tomorrow_weather_text

today_weather, tomorrow_weather = get_weather()
print(f"上海今天的天气: {today_weather}")
print(f"上海明天的天气: {tomorrow_weather}")