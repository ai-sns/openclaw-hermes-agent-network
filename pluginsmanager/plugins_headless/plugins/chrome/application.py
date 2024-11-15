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
from .classes import *
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

    import json

    def run(self, *args, **kwargs):
        """
        Gathers data for each company and returns it as a JSON string.

        :param args: Positional arguments, expects the first argument to be a list of company names.
        :param kwargs: Keyword arguments (not used).
        :return: A JSON string containing the list of names, values, and currencys for each company.
        """

        # Extract the list of companies from the arguments
        companies = args[0].split(",")

        # Initialize lists to store the scraped data
        names = []
        prices = []
        currencys = []

        # Iterate over each company to get the data
        for company in companies:
            # Call the web scraping function to get the data for the company
            name, price, currency = getDatas(company).webScraping()

            # Append the results to the respective lists
            names.append(name)
            prices.append(price)
            currencys.append(currency)

        # Close the web driver
        DRIVER.close()

        # Create a dictionary to structure the results
        result = {
            "company_names": names,
            "stock_prices": prices,
            "prices_currencys": currencys
        }

        # Convert the dictionary to a JSON string and return it
        return json.dumps(result, indent=4)

    def runbak(self,*args,**kwargs):
        city=args[0]

        return f"城市：{city}在{datetime.datetime.now()}的天气是多云."


    def chrome_webScraping(self,*args,**kwargs):
        pass





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

