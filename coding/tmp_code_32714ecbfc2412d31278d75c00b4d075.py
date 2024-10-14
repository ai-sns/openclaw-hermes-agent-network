import requests

def get_weather(api_key):
    city = "Shanghai"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        weather_info = {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "weather_condition": data["weather"][0]["description"]
        }
        return weather_info
    else:
        return {"error": response.status_code, "message": response.text}

# 请在这里替换为您的API密钥
api_key = "YOUR_API_KEY"
weather_data = get_weather(api_key)
print(weather_data)