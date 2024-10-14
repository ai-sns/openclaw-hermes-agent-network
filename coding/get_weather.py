# filename: get_weather.py
import requests

def get_weather(city):
    api_key = 'abcde001'  # 使用你提供的天气API密钥
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        weather_data = response.json()
        return {
            "temperature": weather_data['main']['temp'],
            "description": weather_data['weather'][0]['description'],
            "city": weather_data['name']
        }
    else:
        return None

if __name__ == "__main__":
    city = "Shanghai"
    weather = get_weather(city)
    if weather:
        print(f"城市: {weather['city']}, 温度: {weather['temperature']}°C, 天气描述: {weather['description']}")
    else:
        print("无法获取天气信息")