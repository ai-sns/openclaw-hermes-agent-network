import pandas as pd
from functions import load_data, get_weather_tool_for_call
import numpy as np

# Load the data
data = load_data()

# Calculate the average age
average_age = np.mean(data['age'])

# Calculate 6 + 7
sum_result = 6 + 7

# Get weather for Shanghai
weather_shanghai = get_weather_tool_for_call({"city": "Shanghai"})

# Print results
print(f"Average Age: {average_age}")
print(f"Sum of 6 + 7: {sum_result}")
print(f"Weather in Shanghai: {weather_shanghai}")