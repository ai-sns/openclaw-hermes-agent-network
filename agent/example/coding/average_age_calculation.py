# filename: average_age_calculation.py
import pandas as pd
from functions import load_data

# Step 1: Load data
data = load_data()

# Step 2: Calculate the average age
average_age = data['age'].mean()

# Step 3: Calculate 6 + 7
sum_result = 6 + 7

# Step 4: Print results
print(f"Average age: {average_age}")
print(f"6 + 7 = {sum_result}")