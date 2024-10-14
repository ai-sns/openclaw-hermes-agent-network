import requests
from bs4 import BeautifulSoup

def get_weather():
    url = "http://www.weather.com.cn/weather/101020100.shtml"  # 上海天气页面
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取天气信息
        temperature_tag = soup.find('p', class_='tem')
        weather_condition_tag = soup.find('p', class_='wea')
        humidity_tag = soup.find('span', class_='shidu')
        wind_speed_tag = soup.find('p', class_='win')
        
        # Check if the tags were found
        if temperature_tag and weather_condition_tag and humidity_tag and wind_speed_tag:
            temperature = temperature_tag.find('span').text  # 当前温度
            weather_condition = weather_condition_tag.text  # 天气状况
            humidity = humidity_tag.text.split('：')[1]  # 湿度
            wind_speed = wind_speed_tag.text.split('：')[1]  # 风速
            
            weather_info = {
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather_condition": weather_condition
            }
            return weather_info
        else:
            return {"error": "Could not find one or more weather elements"}
    else:
        return {"error": response.status_code, "message": "Failed to retrieve data"}

weather_data = get_weather()
print(weather_data)