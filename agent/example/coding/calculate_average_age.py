# filename: calculate_average_age.py
people = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35},
    {"name": "David", "age": 40},
    {"name": "Eve", "age": 29},
]

# Calculate the average age
total_age = sum(person["age"] for person in people)
average_age = total_age / len(people)

# Calculate 6 + 7
addition_result = 6 + 7

print(f"Average age: {average_age}")
print(f"6 + 7 = {addition_result}")