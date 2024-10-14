# filename: get_shanghai_weather_details.py
import requests

def get_weather(city):
    url = f'https://wttr.in/{city}?format=j1'  # 使用json格式以获取更详细的信息
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        current = data['current_condition'][0]
        max_temp = current['temp_C']
        min_temp = current['temp_C']
        wind_speed = current['windspeedKmph']

        print(f"城市: {city}")
        print(f"当前温度: {max_temp} °C")
        print(f"最低温度: {min_temp} °C")
        print(f"风速: {wind_speed} km/h")
    else:
        print("无法获取天气信息，请检查城市名称或网络连接。")

get_weather('Shanghai')