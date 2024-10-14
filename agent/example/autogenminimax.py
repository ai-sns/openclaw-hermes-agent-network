from sparkai.frameworks.autogen import SparkAI
from pytalk.agent.llm.minimax import MiniMaxClient
import autogen
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen import AssistantAgent, UserProxyAgent

minimax_config = autogen.config_list_from_json(
    "minimax_autogen.json",
    filter_dict={"model_client_cls": ["MiniMaxClient"]},
)
llm_config = {
    "timeout": 600,
    "cache_seed": None,  # change the seed for different trials
    "config_list": minimax_config,
    "temperature": 0.5,
}

user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    max_consecutive_auto_reply=5,
)

# 1. create an RetrieveAssistantAgent instance named "assistant"
# assistant = RetrieveAssistantAgent(
#     name="assistant",
#     system_message="You are a helpful assistant.",
#     llm_config=llm_config
# )

assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config=llm_config
)


# 注册SparkAI类进入 agent
assistant.register_model_client(model_client_cls=MiniMaxClient)
reply = assistant.generate_reply(messages=[{"content": "介绍一下深圳", "role": "user"}])
print("my reply",reply)
try:

    user_proxy.initiate_chat(
        assistant,
        message="给我发个电子邮件给137200125@qq.com，标题为：你好。内容为：项目开始了。",
    )
except:
    pass

