# filename: get_tomorrow_weather_no_api.py
import requests
from bs4 import BeautifulSoup

def get_tomorrow_weather():
    url = "https://www.qweather.com/weather/101020100.html"  # 这个链接是上海的天气页面
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        tomorrow_forecast = soup.find('div', class_='daily').find_all('div', class_='card')[1]
        date = tomorrow_forecast.find('h4').text.strip()  # 日期
        temperature_high = tomorrow_forecast.find('span', class_='max').text.strip()  # 最高温度
        temperature_low = tomorrow_forecast.find('span', class_='min').text.strip()  # 最低温度
        description = tomorrow_forecast.find('p', class_='txt').text.strip()  # 天气描述
    except (AttributeError, IndexError):
        return None, None, None, None

    return date, temperature_high, temperature_low, description

if __name__ == "__main__":
    date, temperature_high, temperature_low, description = get_tomorrow_weather()
    if temperature_high and temperature_low and description:
        print(f"{date}的最高温度: {temperature_high}, 最低温度: {temperature_low}, 天气描述: {description}")
    else:
        print("无法获取明天的天气信息，可能是网页结构已更改。")