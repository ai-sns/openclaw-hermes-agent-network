# filename: get_shanghai_weather_tomorrow.py
import requests

def get_tomorrow_weather(city):
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    return response.text

shanghai_tomorrow_weather = get_tomorrow_weather("Shanghai")
print(f"上海明天的天气: {shanghai_tomorrow_weather}")