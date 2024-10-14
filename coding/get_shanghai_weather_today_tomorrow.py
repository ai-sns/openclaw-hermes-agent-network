# filename: get_shanghai_weather_today_tomorrow.py
import requests

def get_weather(city):
    today_url = f"https://wttr.in/{city}?format=2"
    tomorrow_url = f"https://wttr.in/{city}?format=3&v"
    
    today_response = requests.get(today_url).text
    tomorrow_response = requests.get(tomorrow_url).text
    
    return today_response, tomorrow_response

shanghai_today_weather, shanghai_tomorrow_weather = get_weather("Shanghai")
print(f"上海今天的天气: {shanghai_today_weather}")
print(f"上海明天的天气: {shanghai_tomorrow_weather}")