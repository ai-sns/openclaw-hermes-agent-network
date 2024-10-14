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
            name='ChatGLM连接器',
            description='用来连接chatglm2-6B模型',
            version='1.0.0'
        )
        print("init meta",self.meta)
        self.conn = http.client.HTTPConnection("61.241.103.48", 18000,timeout=60)
        print("61.241.103.48:18000")
        self.type = "LLM_Connector"
        self.connection_mode = "OpenAI-compatible"

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
        if command[0] == "open_config_dialog":
            print("opendialogue")
            connection.exec_()
        else:
            headers = {
                "Content-Type": "application/json" }
            body = {
                "model": "chatglm3-6b",
                "messages": command,
                "temperature": 0,
                "top_p": 0,
                "max_tokens": 0,
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
                print(f"chatglm连接失败: {e}")
                return "chatglm连接失败"


        return content


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
