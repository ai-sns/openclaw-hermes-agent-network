# filename: fetch_llama_memory_final.py
import requests

def fetch_llama_memory_info():
    url = 'https://huggingface.co/openlm-research/llama-3-405b-pt'
    response = requests.get(url)

    if response.status_code == 200:
        print(response.text)
    else:
        print("Failed to retrieve data")

fetch_llama_memory_info()