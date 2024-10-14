# 导入必要的库
import openai
from typing import Any, Dict, List, Optional, Tuple, Union
from typing import Union, List

from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen import oai
from autogen.oai.client import OpenAIClient,OpenAIWrapper


# 自定义OpenAIClient类
class CustomOpenAIClient(OpenAIClient):
    def __init__(self, client: Union[openai.OpenAI, openai.AzureOpenAI]):
        super().__init__(client)



    def create(self, params: Dict[str, Any]) -> openai.ChatCompletion:
        """自定义create方法"""
        # 这里添加你的自定义逻辑
        print("This is a custom create method")
        print(params)

        # 调用父类的方法，保留原始逻辑
        # response = super().create(params)

        # 可以在此处对response进行修改或进一步处理
        return response


# 修改ConversableAgent类以使用自定义的OpenAIClient
class CustomConversableAgent(ConversableAgent):
    def __init__(self, client: Optional[Union[OpenAIWrapper, CustomOpenAIClient]] = None, **kwargs):
        super().__init__(**kwargs)
        self.client = client if client else CustomOpenAIClient(openai.OpenAI())


# 示例用法
if __name__ == "__main__":
    # 创建自定义的OpenAIClient实例
    custom_client = CustomOpenAIClient(openai.OpenAI(api_key="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"))

    # 创建使用自定义OpenAIClient的ConversableAgent实例
    agent = CustomConversableAgent(client=custom_client,name="cjrok")

    # 调用generate_oai_reply方法
    messages = [{"role": "user", "content": "Hello!"}]
    success, response = agent.generate_oai_reply(messages=messages)

    print(success, response)
