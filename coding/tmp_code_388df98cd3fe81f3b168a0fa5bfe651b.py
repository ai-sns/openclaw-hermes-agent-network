import requests
from bs4 import BeautifulSoup

def get_weather():
    url = "http://www.weather.com.cn/weather/101020100.shtml"  # 上海天气页面
    response = requests.get(url)
    
    if response.status_code == 200:
        response.encoding = 'utf-8'  # Set the correct encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取天气信息
        temperature_tag = soup.find('p', class_='tem')
        weather_condition_tag = soup.find('p', class_='wea')
        wind_speed_tag = soup.find('p', class_='win')
        
        # Check if the tags were found
        if temperature_tag and weather_condition_tag and wind_speed_tag:
            temperature = temperature_tag.find('i').text.strip()  # 当前温度
            weather_condition = weather_condition_tag.text.strip()  # 天气状况
            wind_speed = wind_speed_tag.find('i').text.strip()  # 风速（风级）
            
            weather_info = {
                "temperature": temperature,
                "wind_speed": wind_speed,
                "weather_condition": weather_condition,
                "humidity": "N/A"  # Humidity not available
            }
            return weather_info
        else:
            return {"error": "Could not find one or more weather elements"}
    else:
        return {"error": response.status_code, "message": "Failed to retrieve data"}

weather_data = get_weather()
print(weather_data)