from logging import Logger
import os
import yaml
import qianfan
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
class Connector_LLM_Jiuzhou_yfd_Chatglm_Plugin(PluginCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        self.meta = Meta(
            name='百度文心连接器',
            description='用来连接百度文心大模型',
            version='1.0.0'
        )
        print("init meta",self.meta)
        self.conn = http.client.HTTPSConnection("open.bigmodel.cn",timeout=60)
        print("61.241.103.48:18000")
        self.type = "LLM_Connector"
        self.connection_mode = "OpenAI-customize"

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name='Jiuzhou Device',
            firmware=0xa2c3f,
            protocol='LLM',
            errors=[0x0000]
        )


    def invoke(self,command) -> str:
        # conn = http.client.HTTPConnection("61.241.103.97", 30009)#挪到上面了
        self.conn.close()  # 需要关闭，不然容易断
        stream = True
        connection = OpenAIConnectionDialog(self)
        content=""
        api_key="7381c942a00d9419873da0f978afa822.TCmepxaLAPIV7pO7"
        model="glm-4"#glm-4，glm-3-turbo
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
                print("the stream:",stream)
                if not stream:
                    # 如果不需要流式返回，返回完整响应
                    response_json = response.json()
                    # self.conn.close()  # 需要关闭，不然容易断
                    return ''.join([choice['message']['content'] for choice in response_json['choices']])

                def generator():
                    collected_chunks = []
                    while True:
                        line = response.readline().decode('utf-8')
                        print("the line:",line)
                        if not line:
                            break
                        if line.startswith("data: ") and line.strip() != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                print("chunk",chunk)
                                print("chunkdumps", json.dumps(chunk))

                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    chunk_message = chunk['choices'][0].get('delta', {}).get('content', '')
                                    print("chunk_message R-String", Rf'{chunk_message}')
                                    print("chunk_message",chunk_message)
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
        config=self.get_config()
        config.pop("plugin_name", None)
        config.pop("custom_params", None)
        config.pop("description", None)
        config.pop("parameters",None)
        model_client=LLMConnection(**config)
        return model_client


class LLMConnection():
    def __init__(self, qianfan_ak="", qianfan_sk="", model="", top_p=0.8, temperature=0.8, penalty_score=1.0, stream=True, max_tokens=256, request_timeout=60):
        self.qianfan_ak = qianfan_ak
        self.qianfan_sk = qianfan_sk
        self.model = model
        self.top_p = top_p
        self.temperature = temperature
        self.penalty_score = penalty_score
        self.stream = stream
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        os.environ["QIANFAN_AK"] = qianfan_ak
        os.environ["QIANFAN_SK"] = qianfan_sk
        os.environ["QIANFAN_AK"] = "iSbdJbzkQRvOLlbWaxBVHKLg"
        os.environ["QIANFAN_SK"] = "0Qa9UEYSXowrnQCH2GQkdL887rfeFuKM"
        kwargs = {}
        kwargs["model"] = self.model
        kwargs["ak"] = qianfan_ak
        kwargs["sk"] = qianfan_sk
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout
        self.client = qianfan.ChatCompletion()

    def generate_stream(
            self,
            messages: List
    ):
        kwargs = {}
        kwargs["model"]=self.model
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout

        # 不支撑system这个角色
        if messages[0]["role"] == "system":
            messages = messages[1:]

        for res in self.client.do(messages, **kwargs):
            if res:
                # chunk = res["body"]
                chunk = res["result"]
                print(res["result"])
                yield chunk


    def generate(
            self,
            messages: List
    ):
        kwargs = {}
        kwargs["model"]=self.model
        kwargs["top_p"] = self.top_p
        kwargs["temperature"] = self.temperature
        kwargs["penalty_score"] = self.penalty_score
        kwargs["stream"] = self.stream
        kwargs["request_timeout"] = self.request_timeout

        # 不支撑system这个角色
        if messages[0]["role"] == "system":
            messages = messages[1:]
        res = self.client.do(messages, **kwargs)
        print(res["body"])
        return(res["body"])

