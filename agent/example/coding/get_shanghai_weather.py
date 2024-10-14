# filename: get_shanghai_weather.py
import requests

def get_weather(city):
    url = f'https://wttr.in/{city}?format=3'  # wttr.in 网站提供简单的天气信息
    response = requests.get(url)
    
    if response.status_code == 200:
        print(response.text)  # 输出天气信息
    else:
        print("无法获取天气信息，请检查城市名称或网络连接。")

get_weather('Shanghai')