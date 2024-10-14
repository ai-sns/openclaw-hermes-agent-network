import requests
import json
url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiJQaG90b24iLCJVc2VyTmFtZSI6IlBob3RvbiIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxNzkzMjY2NTE2OTU5OTcwMjcxIiwiUGhvbmUiOiIxMzc2NDMwMzA5MiIsIkdyb3VwSUQiOiIxNzkzMjY2NTE2OTUxNTgxNjYzIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMDYtMjEgMTc6MTc6NDYiLCJpc3MiOiJtaW5pbWF4In0.y5-dSRBh3_9Rygq7PNDbKyguuZPDA6FrBNstXagWqsVEv2L4rsJu0Hwt8roZTfHfHV8zXaywnNrIwBukM7dFgvsgI5Vxg3g-0RtQxcwef3QNiffc0oTsjCwiOkVhSqyAL0AHUDMP-VxIhKHCCoU2DKZBKVJQtC1OgjrvqasO19DQ9hXHDXk2sTlrGvctnjqU5-T98BNBHGb5ej907ReT0hGCbsQZafguujx0xFTU683rKDMlzQOHaB6kVaB40RbJynshcEeI7TCY7ocYDvOSIqh5mz41N61LS7jv_ljRlYgis6o0D2P9ZFCUECfZrQHY-4YAOl3-GhN4n_eDWT8Yrg"
payload = json.dumps({
    "model": "abab6.5-chat",
    "messages": [
        {
            "role": "system",
            "content": "MM智能助理是一款由MiniMax自研的，没有调用其他产品的接口的大型语言模型。MiniMax是一家中国科技公司，一直致力于进行大模型相关的研究。"
        },
        {
            "role": "user",
            "content": "给我详细介绍一下特朗普？"
        },
    ],
    "stream": False,
    "max_tokens": 1000,
    "temperature": 0.7,
    "top_p": 0.7
})
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload, stream=False)#request也要指定stream=True
print(response)
print(response.text)
chunk=json.loads(response.text)
print(chunk['choices'][0].get('message', {}).get('content', ''))
# for line in response.iter_lines():
#     if line:
#         decoded_line = line.decode('utf-8')
#         if decoded_line.startswith("data: ") and decoded_line.strip() != "data: [DONE]":
#             try:
#                 chunk = json.loads(decoded_line[6:])
#                 if 'choices' in chunk and len(chunk['choices']) > 0:
#                     chunk_message = chunk['choices'][0].get('delta', {}).get('content', '')
#                     if chunk_message:
#                         print("chunk_message:", chunk_message)
#                         # yield chunk_message
#             except json.JSONDecodeError:
#                 continue
