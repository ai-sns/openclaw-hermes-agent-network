import pandas as pd
from functions import load_data

# Load the data
data = load_data()

# Calculate the average age
average_age = data['age'].mean()

print(f"The average age is: {average_age}")