import os

import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen.code_utils import (
    DEFAULT_MODEL,
    UNKNOWN,
    execute_code,
    extract_code,
    infer_lang,
)
config_list = {"model": "gpt-4o", "api_key": "sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t","seed": 42,"temperature": 0}
assistant = AssistantAgent(
    name="Monika",
    llm_config = {"model": "gpt-4o", "api_key": "sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t"}
)
user_proxy = UserProxyAgent(
    name="user_proxy",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
    llm_config= {"model": "gpt-4o", "api_key": "sk-proj-U6n3mkrBKd3cOvlOhIhYT3BlbkFJShfJl0xbZtbeVz5j4u1t"}
)
# user_proxy.initiate_chat(
#     assistant,
#     message="""analyse my file, the file location is  C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv"""
#     ,clear_history = True
# )

# 用以下内容替换initiate_chat
while True:
    text = input("请输入：")
    if text == "自动填充代码执行结果":
        text = codeAnswer
    assistant.reset_consecutive_auto_reply_counter(user_proxy)
    user_proxy.reset_consecutive_auto_reply_counter(assistant)
    assistant.reply_at_receive[user_proxy] = True
    user_proxy.send(message=text, recipient=assistant, request_reply=True)
    lastmsg = user_proxy.last_message()
    # 提取代码块
    code = extract_code(lastmsg['content'])
    codeAnswer = ""
    # 它可能一次提供多个代码块，我们试出它的每个结果
    for Acode in code:
        if Acode[0] == "python":
            # 当代码类型是python时运行代码
            # logs_all是代码的执行结果
            logs_all = user_proxy.execute_code_blocks([Acode])
            # 把答案拼起来
            codeAnswer += logs_all[1] + "\n"


