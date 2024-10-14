# filename: get_weather_tomorrow.py
import requests
from bs4 import BeautifulSoup

def get_tomorrow_weather(city_code):
    url = f"https://www.weather.com.cn/weather1d/{city_code}.shtml"
    
    try:
        response = requests.get(url, timeout=10)  # 增加请求超时设置
        response.encoding = 'utf-8'  # 确保使用 UTF-8 编码解析
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            tomorrow_weather = soup.find_all('div', class_='t')  # 找到所有天气信息
            if len(tomorrow_weather) > 1:
                weather_info = tomorrow_weather[1].find('h1').text  # 明天的天气
                temperature = tomorrow_weather[1].find('p', class_='tem').text.strip()  # 明天的温度
                print(f"上海明天的天气: {weather_info}, 温度: {temperature}")
            else:
                print("未找到明天的天气信息。")
        else:
            print("无法获取天气信息，请检查城市名称。")
    except requests.Timeout:
        print("请求超时，请稍后重试。")
    except Exception as e:
        print(f"发生错误: {e}")

# 上海的城市代码为 101020100
get_tomorrow_weather("101020100")