import os

import autogen
from autogen import AssistantAgent, UserProxyAgent

# logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})
logging_session_id = autogen.runtime_logging.start(logger_type="file", config={"filename": "runtime.log"})
print("Logging session ID: " + str(logging_session_id))


config_list = {"model": "gpt-4o-mini", "api_key": "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","seed": 42,"temperature": 0}
assistant = AssistantAgent(
    name="Monika",
    llm_config = {"model": "gpt-4o-mini", "api_key": "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"}
)
user_proxy = UserProxyAgent(
    name="user_proxy",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
    llm_config= {"model": "gpt-4o-mini", "api_key": "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"}
)
user_proxy.initiate_chat(
    assistant,
    # message="""analyse my file, the file location is  C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv""",
    message="""给我查一下上海今天的日出时间和日落时间.""",
    # message="""给我播报一下特朗普2024年大选，今日的相关新闻，要给我翻译成中文.""",
    clear_history = True
)



autogen.runtime_logging.stop()
