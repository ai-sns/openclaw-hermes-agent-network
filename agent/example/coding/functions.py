import pandas

def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def load_data() -> pandas.DataFrame:
    """Load some sample data.

    Returns:
        pandas.DataFrame: A DataFrame with the following columns: name(str), location(str), age(int)
    """
    data = {
        "name": ["John", "Anna", "Peter", "Linda"],
        "location": ["New York", "Paris", "Berlin", "London"],
        "age": [24, 13, 53, 33],
    }
    return pandas.DataFrame(data)


