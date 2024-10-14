# filename: get_weather_using_selenium.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

def get_weather():
    # 设置Chrome驱动
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        driver.get("https://www.weather.com/zh-CN/weather/tomorrow/l/CHXX0008:1:CH")
        time.sleep(5)  # 等待页面加载

        # 提取今日天气信息
        today_weather = driver.find_element(By.XPATH, '//*[@data-testid="CurrentConditions--phraseValue--2xXSr"]').text
        
        # 提取明天天气信息
        tomorrow_weather = driver.find_elements(By.XPATH, '//*[@data-testid="DailyContent--temp--_8DL5"]')[1].text

        return today_weather, tomorrow_weather
    finally:
        driver.quit()

today_weather, tomorrow_weather = get_weather()
print(f"上海今天的天气: {today_weather}")
print(f"上海明天的天气: {tomorrow_weather}")