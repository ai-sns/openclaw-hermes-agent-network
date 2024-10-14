from logging import Logger
import os
import yaml
from ...engine import PluginCore
from ...model import Meta, Device
import http.client
import json
from .OpenAIConnectionDialog import OpenAIConnectionDialog
class Connector_Baichuan2_13B_Plugin(PluginCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        self.meta = Meta(
            name='百川连接器',
            description='用来连接baichuan-13B模型',
            version='1.0.0'
        )
        print("init meta",self.meta)
        self.type = "LLM_Connector"
        self.connection_mode = "OpenAI-compatible"
        self.conn = http.client.HTTPConnection("61.241.103.97", 8501,timeout=60)

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name='Baichuan Device',
            firmware=0xa2c3f,
            protocol='LLM',
            errors=[0x0000]
        )



    def invoke(self,command) -> str:
        # agetnconfigdlg=ConnectionDialog
        connection = OpenAIConnectionDialog(self)
        content=""
        # self.actionConnection.triggered.connect(connection.exec_)  #

        print("baichuan command:",command)

        if command[0]=="open_config_dialog":
            print("opendialogue")
            connection.exec_()
        else:
            headers = {
                "Content-Type": "application/json",
                "X-Auth-Token": "gAAAAABloJ4Hhc_eag3R_ocuwB-E_Ua1OcAmNFGHpc4Qayz06fRWHtNfSU5_uyD9CdMSuhoz_-94yK0FWdUuBaD2_UO3n0g0nbfjvEW3Iw6du056WKqHqcDCq90UTuWnbQ5pmujiu_uYfJmy8CQ7tYML-M5f9Uv8OQ",
                "X-Subject-Token": "gAAAAABloJ4Hhc_eag3R_ocuwB-E_Ua1OcAmNFGHpc4Qayz06fRWHtNfSU5_uyD9CdMSuhoz_-94yK0FWdUuBaD2_UO3n0g0nbfjvEW3Iw6du056WKqHqcDCq90UTuWnbQ5pmujiu_uYfJmy8CQ7tYML-M5f9Uv8OQ"
            }
            body = {
                "model": "baichuan-inc/Baichuan-13B-Chat",
                "messages": command,
                "temperature": 0,
                "top_p": 0,
                "max_length": 0,
                "stream": False
            }

            try:
                self.conn.request("POST", "/v1/chat/completions", json.dumps(body), headers)
                response = self.conn.getresponse()
                data = response.read().decode("utf-8")
                print(data)
                json_data = json.loads(data)
                content = json_data["choices"][0]["message"]["content"]
                print(content)
                # self.conn.close() #暂时不关闭

            except Exception as e:
                print(f"baichuan连接失败: {e}")
                return "baichuan连接失败"
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
