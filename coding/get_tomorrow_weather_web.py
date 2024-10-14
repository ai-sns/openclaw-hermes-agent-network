# filename: get_tomorrow_weather_web.py
import requests
from bs4 import BeautifulSoup

def get_tomorrow_weather():
    # 使用一个不同的天气网站
    url = "https://tianqi.moji.com/weather/china/shanghai"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取明天的天气信息
    try:
        tomorrow_forecast = soup.find_all('div', class_='forecast-item')[1]
        temperature_high = tomorrow_forecast.find('span', class_='temp temp-high').text.strip()
        temperature_low = tomorrow_forecast.find('span', class_='temp temp-low').text.strip()
        description = tomorrow_forecast.find('span', class_='wea').text.strip()
    except (AttributeError, IndexError):
        return None, None, None

    return temperature_high, temperature_low, description

if __name__ == "__main__":
    temperature_high, temperature_low, description = get_tomorrow_weather()
    if temperature_high and temperature_low and description:
        print(f"明天的最高温度: {temperature_high}, 最低温度: {temperature_low}, 天气描述: {description}")
    else:
        print("无法获取明天的天气信息，可能是网页结构已更改。")