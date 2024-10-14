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

config_list = {"model": "gpt-4o-mini", "api_key": "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","cache_seed":None,"seed": None,"temperature": 0}
assistant = AssistantAgent(
    name="Monika",
    system_message="You are a helpful AI assistant. "
    "You can help with simple calculations. "
    "You are a helpful AI assistant.\nSolve tasks using your coding and language skills.\nIn the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.\n    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.\n    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.\nSolve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.\nWhen using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can\'t modify your code. So do not suggest incomplete code which requires users to modify. Don\'t use a code block if it\'s not intended to be executed by the user.\nIf you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don\'t include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use \'print\' function for the output when relevant. Check the execution result returned by the user.\nIf the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can\'t be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.\nWhen you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible."
    "Return 'TERMINATE' when the task is done.",
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
func_name = "calculator_tool_for_call"
fun = globals()[func_name]
description = "A simple calculator"

assistant.register_for_llm(name=func_name, description=description)(fun)
user_proxy.register_for_execution(name=func_name)(fun)

func_name = "get_weather_tool_for_call"
fun = globals()[func_name]
description = "get the weather of a city"

assistant.register_for_llm(name=func_name, description=description)(fun)
user_proxy.register_for_execution(name=func_name)(fun)


print(assistant.llm_config["tools"])

chat_result = user_proxy.initiate_chat(assistant, message="What is (44232 + 13312 / (232 - 32)) * 5 * 1?when you get the answer then tell me the weather of shanghai, at last  draw a cat for me with python and turtle")

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
