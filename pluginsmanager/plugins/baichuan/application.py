import os
from logging import Logger
import os
import yaml
from ...engine import PluginCore
from ...model import Meta, Device
import http.client
import json
from .OpenAIConnectionDialog import OpenAIConnectionDialog

class Connector_LLM_Jiuzhou_yfd_Chatglm_Plugin(PluginCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        self.meta = Meta(
            name='百川在线',
            description='用来连接百川在线模型',
            version='1.0.0'
        )
        print("init meta",self.meta)
        self.conn = http.client.HTTPSConnection("api.baichuan-ai.com",timeout=60)
        print("61.241.103.48:18000")
        self.type = "LLM_Connector"
        self.connection_mode = "OpenAI-compatible"
        modelstr="""
        Baichuan4
Baichuan3-Turbo
Baichuan3-Turbo-128k
Baichuan2-Turbo
Baichuan2-Turbo-192k
        """

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
        api_key="sk-b9911fafe7f5e2d96dc6be3f38a7710e"
        model="Baichuan4"#Baichuan2-Turbo
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
                self.conn.request("POST", "/v1/chat/completions", json.dumps(body), headers)
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
                print(f"百川在线连接失败: {e}")
                return "百川在线连接失败"


        return content

    def get_plugin_cfg(self):
        """
        获取插件配置文件 plugin.yaml 的内容。

        :return: 返回读取的配置字典，如果文件不存在或读取失败则返回 None。
        """
        file_path = os.path.join(os.path.dirname(__file__), 'plugin.yaml')  # 构造配置文件路径

        try:
            # 以 UTF-8 编码打开文件，避免编码错误
            with open(file_path, "r", encoding='utf-8') as f:
                config = yaml.safe_load(f)  # 解析 YAML 文件
        except FileNotFoundError:
            print(f"配置文件未找到: {file_path}")  # 文件未找到时输出提示
        except yaml.YAMLError as e:
            print(f"YAML 解析错误: {e}")  # 解析 YAML 文件时的错误处理
        except UnicodeDecodeError as e:
            print(f"文件解码错误: {e}")  # 处理解码错误

        return config  # 返回配置字典

    def get_config(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            with open(file_path, "r") as f:
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
