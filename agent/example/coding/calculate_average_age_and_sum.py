# filename: calculate_average_age_and_sum.py
import pandas as pd

# Sample data of people
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'location': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
    'age': [23, 34, 45, 29, 54]
}

# Create DataFrame
df = pd.DataFrame(data)

# Calculate average age
average_age = df['age'].mean()

# Calculate 6 + 7
sum_result = 6 + 7

print(f'Average Age: {average_age}')
print(f'Sum of 6 + 7: {sum_result}')