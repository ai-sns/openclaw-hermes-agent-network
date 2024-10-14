# filename: fetch_llama_memory.py
import requests
from bs4 import BeautifulSoup

def fetch_memory_requirement():
    url = 'https://huggingface.co/models?search=llama+3+405B'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 在搜索结果中查找相关信息
    results = soup.find_all('div', class_='model-card')
    
    for result in results:
        if 'LLaMA 3 405B' in result.text:
            print(result.text)

fetch_memory_requirement()