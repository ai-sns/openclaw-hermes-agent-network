from functions import get_weather_tool_for_call

# Calculate 6 + 7
result_addition = 6 + 7

# Get the weather for Shanghai
weather_shanghai = get_weather_tool_for_call({"city": "Shanghai"})

# Print the results
print(f"6 + 7 = {result_addition}")
print(f"Weather in Shanghai: {weather_shanghai}")