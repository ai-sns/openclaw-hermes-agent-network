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

def read_skill(skill_key: str) -> str:
    md = None
    try:
        from backend.modules.skills_registry.service import get_docskills_service

        service = get_docskills_service()
        md = service.read_skill_markdown(skill_key)
    except Exception:
        md = None

    if md is None:
        return f"Error: skill not found: {skill_key}"

    try:
        from backend.modules.skills_registry.service import get_docskills_service

        info = get_docskills_service().get_skill(skill_key)
        runner = (info or {}).get('runner') if isinstance(info, dict) else None
        if isinstance(runner, dict) and runner.get('kind'):
            md = (
                (md or "")
                + "\n\n---\n\n"
                + "If this skill should be executed, call run_doc_skill with this skill_key and then answer the user based on the execution result."
            )
    except Exception:
        pass

    return md