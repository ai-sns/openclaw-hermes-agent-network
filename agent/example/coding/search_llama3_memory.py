# filename: search_llama3_memory.py
import requests
from bs4 import BeautifulSoup

def search_llama3_memory():
    search_query = "Llama3 405B显存需求"
    url = "https://www.google.com/search?q=" + search_query
    headers = {'User-Agent': 'Mozilla/5.0'}  # 模拟浏览器请求

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # 查找和提取搜索结果
        results = soup.find_all('h3')  # 可能标题在h3标签中
        for result in results:
            print(result.text)  # 输出搜索结果标题
    else:
        print("无法访问网页，状态码:", response.status_code)

search_llama3_memory()