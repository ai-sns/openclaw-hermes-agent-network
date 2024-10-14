# filename: get_exchange_rate.py
import requests

def get_exchange_rate():
    response = requests.get('https://api.exchangerate-api.com/v4/latest/CNY')
    data = response.json()
    return data['rates']['USD']

exchange_rate = get_exchange_rate()
print(f'当前人民币对美元的汇率为: {exchange_rate}')