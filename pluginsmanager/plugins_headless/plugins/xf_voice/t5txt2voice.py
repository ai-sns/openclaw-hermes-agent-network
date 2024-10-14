import time
from aip import AipSpeech
from playsound import playsound

""" 你的 APPID AK SK 需要自己注册百度AI账号，建立应用来获取"""



def tospeech(command,speed=5,voice=0):
    # APP_ID = '31922622'
    # API_KEY = "Rjnyd7aMhEbBdOwlw3WUaCj1"
    # SECRET_KEY = "ECf7ThEyIFInT6wtbVyUomxw8iLzhFpS"
    # APP_ID = '61221574'
    # API_KEY = "0QE4RTgXCJdm2exo5yw8vwBm"
    # SECRET_KEY = "BWlFV7jAguJ4aK7Ypi0TjPZSXoOTTN8i"
    #
    APP_ID = '60870585'
    API_KEY = "aIcOXUt9kO9Fcu7zZ3wOuECE"
    SECRET_KEY = "UJKDvoF409LuHtYQ9k9DG54DrFK3Si4n"


    # client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
    # command = '上海:周一 04月03日,阴转小雨 东南风,最低气温15度，最高气温19度'
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
    # speed=5  # 切换语速，范围：0 - 10c
    print('当前语速：%d' % speed)
    # voice=0  # 切换TTS人声，0，1，3，4
    result = client.synthesis(command, 'zh', 1, {'vol': 5, 'spd': speed, 'pit': 5, 'per': voice})
    # 识别正确返回语音二进制 错误则返回dict 参照下面错误码
    if not isinstance(result, dict):
        with open('C:\\fastapi\\aisns\\PyTalk\\auido.mp3', 'wb+') as f:
            f.write(result)
        try:
            playsound('C:\\fastapi\\aisns\\PyTalk\\auido.mp3')
        except:
            print('play error ' + str(voice))
            pass
    else:
        print('get result error ' + str(voice))
    # time.sleep(3)


if __name__=="__main__":
    command = '上海:周一 04月03日,阴转小雨 东南风,最低气温15度，最高气温19度。'
    tospeech(command)




# command = '你好世界'
# client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
# play_count = 0
# while True:
#     for i in range(7, 8):  # 切换语速，范围：0 - 10c
#         print('当前语速：%d' % i)
#         for j in range(4, 5):  # 切换TTS人声，0，1，3，4
#             result = client.synthesis(command, 'zh', 1, {'vol': 5, 'spd': i, 'pit': 5, 'per': j})
#             # 识别正确返回语音二进制 错误则返回dict 参照下面错误码
#             if not isinstance(result, dict):
#                 play_count += 1
#                 with open('auido.mp3', 'wb+') as f:
#                     f.write(result)
#                 try:
#                     playsound('auido.mp3')
#                 except:
#                     play_count -= 1
#                     print('play error ' + str(j))
#                     pass
#             else:
#                 print('get result error ' + str(j))
#             print('播放次数：%d' % play_count)
#             time.sleep(3)

# pip install baidu-aip -i  https://mirror.baidu.com/pypi/simple　