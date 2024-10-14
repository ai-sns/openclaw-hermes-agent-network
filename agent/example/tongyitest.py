from openai import OpenAI
import os

def get_response():
    client = OpenAI(
        api_key="sk-a0aad71425184079a83aca7c2bbe93d1", # 如果您没有配置环境变量，请在此处用您的API Key进行替换
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope SDK的base_url
    )
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
                  {'role': 'user', 'content': '你是谁？'}],
        stream=True
        )
    for chunk in completion:
        print(chunk.model_dump_json())
        for choice in chunk.choices:
            content = choice.delta.content

            print("cjr get the content:", content)

if __name__ == '__main__':
    get_response()
