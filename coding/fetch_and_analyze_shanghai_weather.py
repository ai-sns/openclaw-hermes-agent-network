# filename: fetch_and_analyze_shanghai_weather.py
import requests
from bs4 import BeautifulSoup

url = "https://www.timeanddate.com/weather/china/shanghai"
response = requests.get(url)

# 获取网页源代码
html_source = response.text

# 进行分析
soup = BeautifulSoup(html_source, 'html.parser')

# 提取天气信息
weather_info = soup.find('div', class_='h2').text.strip()
temperature_info = soup.find('div', class_='h2').find_next('span').text.strip()

# 输出分析结果
result = f"Shanghai Weather: {weather_info}, Temperature: {temperature_info}"
print(result)