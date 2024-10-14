import requests

def fetch_html():
    url = "http://www.weather.com.cn/weather/101020100.shtml"  # 上海天气页面
    response = requests.get(url)
    
    if response.status_code == 200:
        print(response.text)  # Print the HTML content
    else:
        print(f"Failed to retrieve data: {response.status_code}")

fetch_html()