# filename: get_weather_shanghai.py
from functions import get_weather_tool_for_call

# Get the weather for Shanghai
weather_response = get_weather_tool_for_call({"city": "Shanghai"})

# Print the weather in Shanghai
print(f"Weather in Shanghai: {weather_response}")