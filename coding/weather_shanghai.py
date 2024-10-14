# filename: weather_shanghai.py
import requests
from datetime import datetime, timedelta

def get_weather(city):
    # Use wttr.in to get weather information
    url = f"https://wttr.in/{city}?format=%Y-%m-%d+%C+%t&u"
    response = requests.get(url)
    
    # Calculate tomorrow's date
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Print the result with a clear label
    weather_info = response.text
    print(f"Weather for Shanghai on {tomorrow_date}: {weather_info}")

city = 'Shanghai'
get_weather(city)