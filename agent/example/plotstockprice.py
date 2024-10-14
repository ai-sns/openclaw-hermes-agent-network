import os
import autogen
from autogen import AssistantAgent, UserProxyAgent

llm_config = {"model": "gpt-4o", "api_key": "sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t"}
assistant = AssistantAgent("assistant", llm_config=llm_config)

user_proxy = UserProxyAgent(
    "user_proxy", code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
    human_input_mode="NEVER",#取值为“ALWAYS”，“TERMINATE”，“NEVER”
)

# Start the chat
user_proxy.initiate_chat(
    assistant,
    #message="Plot a chart of NVDA and TESLA stock price change YTD."
    message="打开google浏览器，然后查询微软，meta，apple三家的股票信息，然后做个ppt文件，并把该ppt发送给文件传输助手"
)
