import pandas as pd
from functions import load_data
import numpy as np

# Load the data
data = load_data()

# Calculate the average age
average_age = np.mean(data['age'])

# Calculate 6 + 7
sum_result = 6 + 7

# Print results
print(f"Average Age: {average_age}")
print(f"Sum of 6 + 7: {sum_result}")

# Since the weather function should be called separately, I'll do that as well
from functions import get_weather_tool_for_call
weather_shanghai = get_weather_tool_for_call({"city": "Shanghai"})
print(f"Weather in Shanghai: {weather_shanghai}")