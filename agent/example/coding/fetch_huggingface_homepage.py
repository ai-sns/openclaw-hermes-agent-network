# filename: fetch_huggingface_homepage.py
import requests

def fetch_huggingface_homepage():
    url = "https://huggingface.co"
    response = requests.get(url)
    
    if response.status_code == 200:
        print(response.text[:1000])  # 输出首页前 1000 个字符
    else:
        print("Failed to retrieve data")

fetch_huggingface_homepage()