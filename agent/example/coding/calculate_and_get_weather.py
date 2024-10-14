# filename: calculate_and_get_weather.py
from functions import get_weather_tool_for_call

# Calculate 6 + 7
result = 6 + 7
print(f"The result of 6 + 7 is: {result}")

# Get the weather for Shanghai using the appropriate function call
weather_info = get_weather_tool_for_call({"city": "Shanghai"})
print(f"The weather in Shanghai is: {weather_info}")