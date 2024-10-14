# filename: get_weather.py
import requests

def get_weather(api_key):
    city = "Shanghai"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Current temperature in {city}: {data['main']['temp']}°C")
        print(f"Weather: {data['weather'][0]['description']}")
    else:
        print("Error fetching weather data.")

# Replace 'your_api_key' with your actual OpenWeatherMap API key
get_weather("your_api_key")