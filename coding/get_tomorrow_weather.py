# filename: get_tomorrow_weather.py
import requests
from bs4 import BeautifulSoup

def get_tomorrow_weather():
    url = "https://www.weather.com/zh-CN/weather/tomorrow/l/CHXX0008:1:CH"  # 上海明天的天气链接
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        tomorrow_forecast = soup.find('section', class_='DailyForecast--Disclosure--1mM3e')
        date = tomorrow_forecast.find('h3').text.strip()  # 日期
        temperature_high = tomorrow_forecast.find_all('span', class_='DailyContent--temp--_8DL5')[0].text.strip()  # 最高温度
        temperature_low = tomorrow_forecast.find_all('span', class_='DailyContent--temp--_8DL5')[1].text.strip()  # 最低温度
        description = tomorrow_forecast.find('span', class_='DailyContent--narrative--hplRl').text.strip()  # 天气描述
    except (AttributeError, IndexError):
        return None, None, None, None

    return date, temperature_high, temperature_low, description

if __name__ == "__main__":
    date, temperature_high, temperature_low, description = get_tomorrow_weather()
    if temperature_high and temperature_low and description:
        print(f"{date}的最高温度: {temperature_high}, 最低温度: {temperature_low}, 天气描述: {description}")
    else:
        print("无法获取明天的天气信息，可能是网页结构已更改。")