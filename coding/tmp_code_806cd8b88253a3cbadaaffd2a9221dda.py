import requests
from bs4 import BeautifulSoup

def get_weather():
    url = "http://www.weather.com.cn/weather/101020100.shtml"  # 上海天气页面
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            # 更新选择器以匹配实际的HTML结构
            temperature = soup.find('p', class_='tem').find('span').text  # 当前温度
            weather_condition = soup.find('p', class_='wea').text  # 天气状况
            humidity = soup.find('span', class_='shidu').text.split('：')[1]  # 湿度
            wind_speed = soup.find('span', class_='win').text.split('：')[1]  # 风速
            
            weather_info = {
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather_condition": weather_condition
            }
            return weather_info
        except AttributeError:
            return {"error": "Could not find the required weather information. Please check the HTML structure."}
    else:
        return {"error": response.status_code, "message": "Failed to retrieve data"}

weather_data = get_weather()
print(weather_data)