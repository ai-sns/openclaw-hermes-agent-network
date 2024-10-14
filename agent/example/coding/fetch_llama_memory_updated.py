# filename: fetch_llama_memory_updated.py
import requests
from bs4 import BeautifulSoup

def fetch_llama_memory_requirement():
    url = 'https://huggingface.co/docs/transformers/model_doc/llama'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 查找关于 LLaMA 模型的显存需求的信息
    paragraphs = soup.find_all('p')
    
    for paragraph in paragraphs:
        if '405B' in paragraph.text or 'memory' in paragraph.text.lower():
            print(paragraph.text)

fetch_llama_memory_requirement()