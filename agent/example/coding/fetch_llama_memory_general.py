# filename: fetch_llama_memory_general.py
import requests
from bs4 import BeautifulSoup

def fetch_llama_memory_info():
    url = 'https://huggingface.co/models?search=llama'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # 查找所有相关模型的链接
        models = soup.find_all('a', class_='model-link')
        
        for model in models:
            if 'Llama' in model.text:
                print(model.text, model['href'])

fetch_llama_memory_info()