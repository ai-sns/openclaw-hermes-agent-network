import os
import os
import sys
import openai
import yaml
from logging import Logger

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

class Main():
    def __init__(self,record):
        id = record.id
        self.record=query_PluginMng(id=id)

    def open_config_dialog(self):
        connection = OpenAIConnectionDialog(self)
        connection.exec_()

    def run(self,*args,**kwargs):
        self.question=args[0]
        self.messages=args[1]
        self.browser_page=args[2]
        self.task_id=args[3]
        answer = self.generate_image(self.question)

        return (answer,"")

    def generate_imagebak(self, prompt, model="dall-e-3", n=1, size="1024x1024"):
        # 更新模型和参数的说明
        """
        The size of the generated images. Must be one of 1024x1024, 1792x1024, or 1024x1792 for dall-e-3 models.
        The number of images to generate. Must be 1 for dall-e-3.
        """

        url = "https://dalle.feiyuyu.net/v1/images/generations"
        api_key = "ae51ca53-29b1"  # 更新为您提供的 Bearer Token

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        data = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size
        }

        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=data)
        print("dallurl:", url)

        # 检查响应状态
        if response.status_code != 200:
            print("Error:", response.text)
            return []

        # 提取 URL 列表
        urls = [datum['url'] for datum in response.json().get('data', [])]
        print(urls)

        for i in range(len(urls)):
            image_name = generate_random_id() + ".png"

            task_id = self.task_id
            directory_path = os.path.join('resource', 'attachment', 'chat', task_id)
            os.makedirs(directory_path, exist_ok=True)

            save_path = os.path.join('resource', 'attachment', 'chat', task_id, image_name)

            save_path = os.path.join('resource', 'attachment', 'chat', image_name)
            download_image(urls[i], save_path)
            save_path = os.path.abspath(save_path).replace("\\", "/")
            urls[i] = save_path  # 直接替换 urls 列表中对应位置的值

        img_element = ''.join(f"""<br><a href="#" onclick="open_attachment('{url}');return false;" style="color:blue"><img src="file:///{url}" alt="{url}" style="width:300px;height:auto;" /></a><br>""" for url in urls)
        print(img_element)

        # 添加附件元素到页面中
        self.browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += `' + img_element + '`')
        self.browser_page.runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

        return img_element  # 返回生成的图像 URL 列表

    def generate_image(self, prompt, model="dall-e-2", n=2, size="512x512"):
        # ***dall-e-3的n必须是1，size只能是：'1024x1024', '1024x1792', '1792x1024'
        """
        The size of the generated images. Must be one of 256x256, 512x512, or 1024x1024 for dall-e-2. Must be one of 1024x1024, 1792x1024, or 1024x1792 for dall-e-3 models.
        The number of images to generate. Must be between 1 and 10. For dall-e-3, only n=1 is supported.

        """

        openai.api_key = "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"
        response = openai.images.generate(
            model=model,
            prompt=prompt,
            n=n,
            size=size,
            response_format="url",
        )

        # 提取 URL 列表
        # urls = [data['url'] for data in response['data']]
        urls = [datum.url for datum in response.data]

        for i in range(len(urls)):
            image_name = generate_random_id() + ".png"

            task_id=self.task_id
            directory_path = os.path.join('resource', 'attachment', 'chat', task_id)
            os.makedirs(directory_path, exist_ok=True)

            save_path = os.path.join('resource', 'attachment', 'chat',task_id, image_name)
            download_image(urls[i], save_path)
            save_path = os.path.abspath(save_path).replace("\\", "/")
            # urls[i] ="file:///"+ save_path  # 直接替换 urls 列表中对应位置的值
            urls[i] = save_path  # 直接替换 urls 列表中对应位置的值

        # message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
        # self.browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br>"')
        # message = f"""{prompt}"""
        # self.browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br><br>"')
        # modelname = model
        # message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
        # self.browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '"')

        # 创建新的附件元素
        # attachment_element = f"""<br><br><a href="#" onclick="open_attachment('{new_file_path}');return false;" style="color:blue"><img src="file:///{image_file_path}" alt="{file_name}" style="width:300px;height:auto;" /></a><br><br>"""

        img_element = ''.join(f"""<br><a href="#" onclick="open_attachment('{url}');return false;" style="color:blue"><img src="file:///{url}" alt="{url}" style="width:300px;height:auto;" /></a><br>""" for url in urls)
        print(img_element)
        # 添加附件元素到页面中
        self.browser_page.runJavaScript('document.getElementById("allcontent").innerHTML += `' + img_element + '`')
        self.browser_page.runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

        return img_element  # 返回生成的图像 URL 列表





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

