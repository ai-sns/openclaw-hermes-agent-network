
from  t1_record import my_record
# from  baidu.tuling.t2totxt import listen
from  sdk_2text import XF_text
from sdk_2voice import text_to_voice
from baidu.tuling.t3calltuling import Turing
from baidu.tuling.t4tospeech import speak1
from baidu.tuling.t5txt2voice import tospeech


# 语音合成，输出机器人的回答
if __name__ == '__main__':
    while True:
        path="my01.wav"
        my_record()
        request =XF_text(path,16000)
        # response = Turing(request)
        response="今天天气真好！"
        text_to_voice(response)
        speak1(response)
        tospeech(response)
        break
