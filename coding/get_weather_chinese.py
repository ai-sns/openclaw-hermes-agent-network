# filename: get_weather_chinese.py
import requests
from bs4 import BeautifulSoup

def get_weather(city_code):
    url = f"https://www.weather.com.cn/weather1d/{city_code}.shtml"
    
    response = requests.get(url)
    response.encoding = 'utf-8'  # 确保使用 UTF-8 编码解析
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        weather_info = soup.find('div', class_='t').find('h1').text
        temperature = soup.find('p', class_='tem').find('span').text
        print(f"上海的天气: {weather_info}, 温度: {temperature}°C")
    else:
        print("无法获取天气信息，请检查城市名称。")

# 上海的城市代码为 101020100
get_weather("101020100")