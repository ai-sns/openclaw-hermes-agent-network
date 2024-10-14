#https://microsoft.github.io/autogen/docs/topics/code-execution/user-defined-functions
#本地自定义函数
import pandas

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(python_packages=["pandas"], global_imports=["pandas"])
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

def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[add_two_numbers, load_data])

codebakok = f"""
from functions import add_two_numbers

print(add_two_numbers(1, 2))
"""

code = f"""
from {LocalCommandLineCodeExecutor.functions_module} import add_two_numbers

print(add_two_numbers(1, 2))
"""

print(
    executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ]
    )
)


codebak = f"""
from functions import add_two_numbers

print(add_two_numbers(1, 2))
"""

code = f"""
from {LocalCommandLineCodeExecutor.functions_module} import load_data

print(load_data())
"""

result = executor.execute_code_blocks(
    code_blocks=[
        CodeBlock(language="python", code=code),
    ]
)

print(result.output)


nlnl = "\n\n"
code_writer_system_message = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

# Add on the new functions
code_writer_system_message += executor.format_functions_for_prompt()

print(code_writer_system_message)

import os

from autogen import ConversableAgent

code_writer_agent = ConversableAgent(
    "code_writer",
    system_message=code_writer_system_message,
    llm_config={"config_list": [{"model": "gpt-4o-mini", "api_key": "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"}]},
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=2,
    human_input_mode="NEVER",
)

code_executor_agent = ConversableAgent(
    name="code_executor_agent",
    llm_config=False,
    code_execution_config={
        "executor": executor,
    },
    human_input_mode="NEVER",
)

chat_result = code_executor_agent.initiate_chat(
    code_writer_agent,
    # message="Please use the load_data function to load the data and please calculate the average age of all people.",
    message="Please give me some data of people and calculate the average age of all people and what is 6+7,可以使用提供给你的代码函数",
    summary_method="reflection_with_llm",
)
