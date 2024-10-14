# filename: task_processing.py

import requests
from functions import convert_rmb_to_usd_v2

# Step 1: 查询上海的天气
def get_weather(city):
    api_key = "your_api_key"  # 请替换为实际获取的API Key
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}q={city}&appid={api_key}&units=metric"

    response = requests.get(complete_url)
    data = response.json()

    if data["cod"] != "404":
        main = data["main"]
        weather_description = data["weather"][0]["description"]
        return f"{city}当前的天气是: {weather_description}，温度: {main['temp']}°C"
    else:
        return "城市未找到"

city = "Shanghai"
weather_info = get_weather(city)

# Step 2: 货币兑换任务
amount_rmb = 10
amount_usd = convert_rmb_to_usd_v2(amount_rmb)

# 输出结果
print(f"上海当前的天气: {weather_info}")
print(f"10人民币兑换成美元是: {amount_usd}美元")