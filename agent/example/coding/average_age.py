# filename: average_age.py
import pandas as pd
from functions import load_data

# Load data
data = load_data()

# Calculate average age
average_age = data['age'].mean()
print(f"The average age of all people is: {average_age}")

# Calculate 6 + 7
result = 6 + 7
print(f"6 + 7 is: {result}")