from datetime import datetime
from typing import Annotated, Literal

Operator = Literal["+", "-", "*", "/"]


def calculator_tool_for_call(a: int, b: int, operator: Annotated[Operator, "operator"]) -> int:
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return int(a / b)
    else:
        raise ValueError("Invalid operator")

def get_weather_sbi(city: str) -> str:
    """
    this function is used to get the weather of a city
    city:a city name
    """
    return f"The weather forecast for {city} at {datetime.now()} is sunny."

def test_cjrok_tool_for_call(w:str) -> str:
    print(w)