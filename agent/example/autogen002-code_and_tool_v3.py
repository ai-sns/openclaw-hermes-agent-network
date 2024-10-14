import os
import sys
sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")
import autogen
from autogen import AssistantAgent, UserProxyAgent

import os
from autogen import ConversableAgent
from typing import Annotated, Literal
from tools import *


#https://microsoft.github.io/autogen/docs/topics/code-execution/user-defined-functions
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

# def add_two_numbers(a: int, b: int) -> int:
#     """Add two numbers together."""
#     return a + b

from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

work_dir = Path("coding")
work_dir.mkdir(exist_ok=True)

# executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[add_two_numbers, load_data])#使用codebakok这种徐娅有functions
executor = LocalCommandLineCodeExecutor(work_dir=work_dir)#使用code这种直接指明functions文件的就不需要这里写functions这个参数了

codebakok = f"""
from functions import add_two_numbers

print(add_two_numbers(1, 2))
"""

code = f"""
from functions import add_two_numbers

print(add_two_numbers(2, 2))
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
from functions import load_data

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

system_message="""You are a helpful AI assistant. 
    You can help with simple calculations. 
    You are a helpful AI assistant.\nSolve tasks using your coding and language skills.\nIn the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.\n    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.\n    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.\nSolve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.\nWhen using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can\'t modify your code. So do not suggest incomplete code which requires users to modify. Don\'t use a code block if it\'s not intended to be executed by the user.\nIf you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don\'t include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use \'print\' function for the output when relevant. Check the execution result returned by the user.\nIf the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can\'t be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.\nWhen you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible."
    when you want to load data,you can generate code with load_data function that i provided.   do not suggested  tool call with load_data
    when you want to get weather info you must use tool call provided by openai.
    Return 'TERMINATE' when the task is done."""

system_message=system_message+code_writer_system_message


config_list = {"model": "gpt-4o-mini", "api_key": "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","cache_seed":None,"seed": None,"temperature": 0}
assistant = AssistantAgent(
    name="Monika",
    system_message=system_message,
    llm_config = {"model": "gpt-4o-mini", "api_key": "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","stream":True,"seed": 41,"cache_seed":None,}
)
user_proxy = UserProxyAgent(
    name="user_proxy",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},

)
# user_proxy = ConversableAgent(
#     name="User",
#     llm_config=False,
#     is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
#     human_input_mode="NEVER",
# )


# Register the tool signature with the assistant agent.
# cal = Calculator()
# t=cal.calculator
# func_name = "calculator_tool_for_call"
# fun = globals()[func_name]
# description = "A simple calculator"
#
# assistant.register_for_llm(name=func_name, description=description)(fun)
# user_proxy.register_for_execution(name=func_name)(fun)
#
func_name = "get_weather_tool_for_call"
fun = globals()[func_name]
description = "get the weather of a city"

assistant.register_for_llm(name=func_name, description=description)(fun)
user_proxy.register_for_execution(name=func_name)(fun)


# print(assistant.llm_config["tools"])

# executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[add_two_numbers, load_data])
executor = LocalCommandLineCodeExecutor(work_dir=work_dir)

chat_result = user_proxy.initiate_chat(
    assistant,
    # message="Please use the load_data function to load the data and please calculate the average age of all people.",
    message="Please give me some data of people and calculate the average age of all people and what is 6+7,可以使用提供给你的代码函数,告诉我上海的天气，请一定注意，do not use tool call or function call with load_data function call和tool call一定不要用load_data",
    summary_method="reflection_with_llm",
)



# chat_result = user_proxy.initiate_chat(assistant, message="What is (44232 + 13312 / (232 - 32)) * 5 * 1?when you get the answer then tell me the weather of shanghai,and Please use the load_data function to load the data and please calculate the average age of all people. at last  draw a cat for me with python and turtle")

# user_proxy.initiate_chat(
#     assistant,
#     # message="""analyse my file, the file location is  C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv"""
#     message = """给我画个哆啦A梦""",
#     # message = """给我查一下部署LLama3 405B需要多少显存""",
#     clear_history = True
#
# )

# 用以下内容替换initiate_chat
# while True:
#     text = input("请输入：")
#     assistant.reset_consecutive_auto_reply_counter(user_proxy)
#     user_proxy.reset_consecutive_auto_reply_counter(assistant)
#     assistant.reply_at_receive[user_proxy] = True
#     user_proxy.send(message=text, recipient=assistant, request_reply=True)
#     lastmsg = user_proxy.last_message()
#     print(lastmsg)
#
# message = user_proxy.last_message()
# print(f"message---cjrok:{message}")
