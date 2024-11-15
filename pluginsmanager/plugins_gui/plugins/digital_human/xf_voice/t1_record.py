# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple speechrecognition

import speech_recognition as sr
# import sounddevice as sd

# Use SpeechRecognition to record 使用语音识别包录制音频
# 语音生产文件就需要进行录音，将我们说的话保存下来
def my_record(rate=16000):
    r = sr.Recognizer()
    with sr.Microphone(sample_rate=rate) as source:
        print('please say something')
        audio = r.listen(source,timeout=1)
    with open('my01.wav', 'wb') as f:
        f.write(audio.get_wav_data())
    print('录音完成！')



if __name__ == '__main__':
    my_record()
    # record()
