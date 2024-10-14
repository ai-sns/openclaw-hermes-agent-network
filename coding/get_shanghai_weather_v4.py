# filename: get_shanghai_weather_v4.py
import requests

def get_weather(city):
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    return response.text

shanghai_weather = get_weather("Shanghai")
print(f"上海的天气: {shanghai_weather}")