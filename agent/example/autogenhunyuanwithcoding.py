from sparkai.frameworks.autogen import SparkAI
from pytalk.agent.llm.hunyuan import HunYuanClient
import autogen
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen import AssistantAgent, UserProxyAgent

minimax_config = autogen.config_list_from_json(
    "hunyuan_autogen.json",
    filter_dict={"model_client_cls": ["HunYuanClient"]},
)
llm_config = {
    "timeout": 600,
    "cache_seed": None,  # change the seed for different trials
    "config_list": minimax_config,
    "temperature": 0.5,
}

user_proxy = UserProxyAgent(
    "user_proxy",
    code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    max_consecutive_auto_reply=2,

)

# 1. create an RetrieveAssistantAgent instance named "assistant"
# assistant = RetrieveAssistantAgent(
#     name="assistant",
#     system_message="You are a helpful assistant.",
#     llm_config=llm_config
# )

assistant = AssistantAgent(
    name="assistant",
    llm_config=llm_config
)


# 注册SparkAI类进入 agent
assistant.register_model_client(model_client_cls=HunYuanClient)

# reply = assistant.generate_reply(messages=[{"content": "介绍一下深圳", "role": "user"}])
# print("my reply:",reply)
try:

    user_proxy.initiate_chat(
        assistant,
        # message="""analyse my file, the file location is  C:\dev\ai-sns\autogen\MieruData\data\inputData\Mytest.csv""",
        message="""给我写个python的冒泡排序算法并执行看看效果""",
        clear_history=True
    )
except:
    pass

