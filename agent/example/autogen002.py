import os

import autogen
from autogen import AssistantAgent, UserProxyAgent
config_list = {"model": "gpt-4o-mini", "api_key": "sk-proj-dTscQ85YyiauTbnIjJJ8T3BlbkFJ0eXdobM7Tm5hpDNrQjiW","seed": 42,"temperature": 0}
assistant = AssistantAgent(
    name="Monika",
    llm_config = {"model": "gpt-4o-mini", "api_key": "sk-proj-dTscQ85YyiauTbnIjJJ8T3BlbkFJ0eXdobM7Tm5hpDNrQjiW","stream":True}
)
user_proxy = UserProxyAgent(
    name="user_proxy",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
    llm_config= {"model": "gpt-4o", "api_key": "sk-proj-dTscQ85YyiauTbnIjJJ8T3BlbkFJ0eXdobM7Tm5hpDNrQjiW"}
)
user_proxy.initiate_chat(
    assistant,
    # message="""analyse my file, the file location is  C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv"""
    message = """给我画个哆啦A梦""",
    clear_history = True

)

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
