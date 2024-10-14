from autogen import oai
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

def TestChat():
    # create a text completion request
    response = oai.Completion.create(
        config_list=[
            {
                "model": "chatglm3-6b",
                "api_base": "http://61.241.103.48:18000/v1",
                "api_type": "open_ai",
                "api_key": "NULL",  # just a placeholder
            }
        ],
        prompt="Hi",
    )
    print(response)

    # create a chat completion request
    response = oai.ChatCompletion.create(
        config_list=[
            {
                "model": "chatglm3-6b",
                "api_base": "http://61.241.103.48:18000/v1",
                "api_type": "open_ai",
                "api_key": "NULL",
            }
        ],
        messages=[{"role": "user", "content": "Hi"}]
    )
    print(response)


def TestAutoGen():
    config_list = [
        {
            "model": "chatglm3-6b",
            "api_base": "http://61.241.103.48:18000/v1",
            "api_type": "open_ai",
            "api_key": "NULL",
        }
    ]
    assistant = AssistantAgent("assistant", llm_config={
                               "config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy", code_execution_config={"work_dir": "coding","use_docker":False})
    user_proxy.initiate_chat(
        assistant, message="用react.js写一个用户登录程序")


if __name__ == '__main__':
    TestChat()
    TestAutoGen()
