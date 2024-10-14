# filename: calculate_age_and_sum.py
import pandas as pd

# Step 1: Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'location': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
    'age': [28, 34, 25, 42, 30]
}

# Step 2: Create DataFrame
df = pd.DataFrame(data)

# Step 3: Calculate average age
average_age = df['age'].mean()

# Step 4: Calculate 6 + 7
sum_result = 6 + 7

# Printing results
print(f"The average age of the people is: {average_age}")
print(f"The result of 6 + 7 is: {sum_result}")