import pyttsx3
import win32com.client
# 初始化语音
def speak1(txt):
    engine = pyttsx3.init() # 初始化语音库
    # 设置语速
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate-50)
    # 输出语音
    engine.say(txt) # 合成语音
    engine.runAndWait()

# 使用python进行编程就是有很多好处，比如音频的输出我们就可以采用多种方式，下面提供一种更加简便的音频输出方式：

def speak2(txt):
    speaker = win32com.client.Dispatch('SAPI.SpVoice')
    speaker.Speak(txt)

if __name__ == '__main__':
    txt = "上海:周一 04月03日,阴转小雨 东南风,最低气温15度，最高气温19度。"
    speak1(txt)
    speak2(txt)