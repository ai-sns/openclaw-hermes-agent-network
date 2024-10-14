# filename: get_weather_wttrin.py
import requests

def get_weather(city):
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    return response.text

if __name__ == "__main__":
    city = "Shanghai"
    weather_info = get_weather(city)
    print(weather_info)