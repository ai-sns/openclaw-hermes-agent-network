from logging import Logger
import os
import yaml
from ...engine import PluginCore
from ...model import Meta, Device
import http.client
import json
from .OpenAIConnectionDialog import OpenAIConnectionDialog

from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models


class Connector_LLM_Jiuzhou_yfd_Chatglm_Plugin(PluginCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        self.meta = Meta(
            name='腾讯混元连接器',
            description='用来连接腾讯混元在线模型',
            version='1.0.0'
        )
        print("init meta", self.meta)
        self.conn = http.client.HTTPSConnection("open.bigmodel.cn", timeout=60)
        print("61.241.103.48:18000")
        self.type = "LLM_Connector"
        self.connection_mode = "Customize"

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name='Jiuzhou Device',
            firmware=0xa2c3f,
            protocol='LLM',
            errors=[0x0000]
        )

    def invoke(self, command) -> str:
        # conn = http.client.HTTPConnection("61.241.103.97", 30009)#挪到上面了
        self.conn.close()  # 需要关闭，不然容易断
        stream = True
        connection = OpenAIConnectionDialog(self)
        content = ""
        api_key = "7381c942a00d9419873da0f978afa822.TCmepxaLAPIV7pO7"
        model = "glm-4"  # glm-4，glm-3-turbo
        if command[0] == "open_config_dialog":
            print("opendialogue")
            connection.exec_()
        else:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key
            }

            body = {
                "model": model,
                "messages": command,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048,
                "stream": stream
            }

            try:
                self.conn.request("POST", "/api/paas/v4/chat/completions", json.dumps(body), headers)
                response = self.conn.getresponse()
                # data = response.read().decode("utf-8")
                # print(data)
                # json_data = json.loads(data)
                # content = json_data["choices"][0]["message"]["content"]
                # print(content)
                print("the stream:", stream)
                if not stream:
                    # 如果不需要流式返回，返回完整响应
                    response_json = response.json()
                    # self.conn.close()  # 需要关闭，不然容易断
                    return ''.join([choice['message']['content'] for choice in response_json['choices']])

                def generator():
                    collected_chunks = []
                    while True:
                        line = response.readline().decode('utf-8')
                        print("the line:", line)
                        if not line:
                            break
                        if line.startswith("data: ") and line.strip() != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                print("chunk", chunk)
                                print("chunkdumps", json.dumps(chunk))

                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    chunk_message = chunk['choices'][0].get('delta', {}).get('content', '')
                                    print("chunk_message R-String", Rf'{chunk_message}')
                                    print("chunk_message", chunk_message)
                                    if chunk_message:
                                        collected_chunks.append(chunk_message)
                                        yield chunk_message
                            except json.JSONDecodeError:
                                # 忽略无效的 JSON 数据行
                                continue

                # self.conn.close()  # 需要关闭，不然容易断
                return generator()








            except Exception as e:
                print(f"ChatGLM在线连接失败: {e}")
                return "ChatGLM在线连接失败"

        return content

    def get_config(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            pass

        return config

    def set_config(self, new_config):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            with open(file_path, "w") as f:
                yaml.safe_dump(new_config, f)
        except Exception as e:
            print(f"Error while saving YAML file: {e}")

    def get_model(self):
        config = self.get_config()
        config.pop("plugin_name", None)
        config.pop("custom_params", None)
        config.pop("description", None)
        config.pop("parameters", None)
        model_client = LLMConnection(**config)
        return model_client


class LLMConnection():
    def __init__(self, secret_id="", secret_key="", model="", top_p=0.8, temperature=0.8, stream=True, max_tokens=256):
        self.model = model
        self.top_p = top_p
        self.temperature = temperature
        self.stream = stream
        self.max_tokens = max_tokens
        cred = credential.Credential(
            secret_id,
            secret_key)

        cpf = ClientProfile()
        # 预先建立连接可以降低访问延迟
        cpf.httpProfile.pre_conn_pool_size = 3
        self.client = hunyuan_client.HunyuanClient(cred, "ap-guangzhou", cpf)

    def generate_stream(
            self,
            messages: List
    ):
        req = models.ChatCompletionsRequest()

        hunyuan_messages = []

        for message in messages:
            msg = models.Message()
            msg.Role = message["role"]
            msg.Content = message["content"]
            hunyuan_messages.append(msg)
        req.Messages = hunyuan_messages

        # hunyuan ChatStd/ChatPro 同时支持 stream 和非 stream 的情况
        req.Stream = True
        req.Model = self.model
        client = self.client
        resp = client.ChatCompletions(req)
        if req.Stream:  # stream 示例
            for event in resp:
                print(event["data"])
                data = json.loads(event['data'])
                for choice in data['Choices']:
                    chunk = choice['Delta']['Content']
                    yield chunk

    def generate(
            self,
            messages: List
    ):
        req = models.ChatCompletionsRequest()

        hunyuan_messages = []

        for message in messages:
            msg = models.Message()
            msg.Role = message["role"]
            msg.Content = message["content"]
            hunyuan_messages.append(msg)
        req.Messages = hunyuan_messages

        # hunyuan ChatStd/ChatPro 同时支持 stream 和非 stream 的情况
        req.Stream = False
        req.Model = self.model
        client = self.client
        resp = client.ChatCompletions(req)
        content = resp.Choices[0].Message.Content
        return content
