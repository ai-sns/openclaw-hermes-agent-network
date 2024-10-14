import pandas as pd
from functions import load_data
import numpy as np

# Load the data
data = load_data()

# Calculate the average age
average_age = np.mean(data['age'])

# Calculate 6 + 7
sum_result = 6 + 7

# Print results for average age and sum
print(f"Average Age: {average_age}")
print(f"Sum of 6 + 7: {sum_result}")

# Directly calling the weather tool
from functions import multi_tool_use

# Get weather for Shanghai
weather_response = multi_tool_use.parallel({
    "tool_uses": [{
        "recipient_name": "functions.get_weather_tool_for_call",
        "parameters": {"city": "Shanghai"}
    }]
})

# Print the weather in Shanghai
print(f"Weather in Shanghai: {weather_response[0]}")