import os
import os
import sys
import openai
import yaml
from logging import Logger
# from datetime import datetime
from pytalk.pluginsmanager.engine import PluginCore
from pytalk.pluginsmanager.model import Meta, Device
from logging import Logger
import json
import requests

from pytalk.util import generate_random_id, download_image
from .OpenAIConnectionDialog import OpenAIConnectionDialog
sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")
sys.path.append("../../../..")
sys.path.append("../../../../..")
from db.DBFactory import query_PluginMng
import pyautogui
import pyperclip
import os
import time
pyautogui.PAUSE = 0.5

class Main():
    def __init__(self,record):
        id = record.id
        self.record=query_PluginMng(id=id)

    def open_config_dialog(self):
        connection = OpenAIConnectionDialog(self)
        connection.exec_()

    import json

    def click_image_position(self,img):
        time.sleep(1)
        image_1 = pyautogui.locateOnScreen(img, grayscale=True, confidence=0.7)
        time.sleep(1)
        center = pyautogui.center(image_1)
        pyautogui.click(center)

    def run(self, *args, **kwargs):
        while True:
            try:
                print("准备发文件...")
                os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
                time.sleep(2)
                self.click_image_position("search.png")
                name = args[1]
                pyperclip.copy(name)
                # 模拟按下和释放Ctr1键和V键
                pyautogui.hotkey('ctrl', 'v')
                pyautogui.press('enter')
                time.sleep(1)  # 避免操作过快
                self.click_image_position("sendfile.png")
                # file_path = 'C:\\testfile\\market-5-2024.pptx'
                file_path = args[0]
                print("file_path:",file_path)
                pyperclip.copy(file_path)
                pyautogui.hotkey('ctrl', 'v')
                pyautogui.press('enter')
                time.sleep(1)
                pyautogui.press('enter')
                break

            except:

                break

        return "发送完成。"




class Connector_OpenAI_Plugin(PluginCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)
        self.meta = Meta(
            name='Draw',
            description='用来画画',
            version='1.0.0'
        )
        print("init meta", self.meta)
        self.type = "Tool_Headless"
        self.connection_mode="OpenAI"

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name='Jiuzhou Device',
            firmware=0xa2c3f,
            protocol='LLM',
            errors=[0x0000]
        )



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


    def invoke(self, command) -> str:
        api_key = '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'
        stream = True
        connection = OpenAIConnectionDialog(self)
        content = ""

        if command[0] == "open_config_dialog":
            print("opendialogue")
            connection.exec_()
        else:
            headers = {
                'Authorization': f'Bearer {api_key}',
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": command,
                "max_tokens":4000,
                "temperature": 0.9,
                "top_p": 1.0,
                "n": 1,
                "stop": None,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.6,
                "stream": stream
            }

            try:
                api_url="https://api.openai.com/v1/chat/completions"
                # response = requests.post(api_url, json=body, headers=headers, stream=stream)
                response = requests.post(api_url, headers=headers, data=json.dumps(data), stream=stream)

                if not stream:
                    response_json = response.json()
                    print("response_json:",response_json)
                    return ''.join([choice['message']['content'] for choice in response_json['choices']])

                def generator():
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith("data: ") and decoded_line.strip() != "data: [DONE]":
                                try:
                                    chunk = json.loads(decoded_line[6:])
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        chunk_message = chunk['choices'][0].get('delta', {}).get('content', '')
                                        if chunk_message:
                                            print("chunk_message:",chunk_message)
                                            yield chunk_message
                                except json.JSONDecodeError:
                                    continue

                return generator()

            except Exception as e:
                print(f"Openai连接失败: {e}")
                return "Openai连接失败"

        return content

