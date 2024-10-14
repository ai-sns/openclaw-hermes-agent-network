# 音频文件转文字：采用百度的语音识别python-SDK
# 百度语音识别API配置参数
from aip import AipSpeech

APP_ID = '60870585'
API_KEY = "aIcOXUt9kO9Fcu7zZ3wOuECE"
SECRET_KEY = "UJKDvoF409LuHtYQ9k9DG54DrFK3Si4n"
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
path = 'my01.wav'
# 将语音转文本STT
def listen():
# 读取录音文件
    with open(path, 'rb') as fp:
        voices = fp.read()
        try:
# 参数dev_pid：1536普通话(支持简单的英文识别)、1537普通话(纯中文识别)、1737英语、1637粤语、1837四川话、1936普通话远场
            result = client.asr(voices, 'wav', 16000, {'dev_pid': 1537, })
# result = CLIENT.asr(get_file_content(path), 'wav', 16000, {'lan': 'zh', })
# print(result)
# print(result['result'][0])
# print(result)
            result_text = result['result'][0]
            print('you said: ' + result_text)
            return result_text
        except KeyError:
            print('KeyError')

if __name__ == '__main__':
    listen()
