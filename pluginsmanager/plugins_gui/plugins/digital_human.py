# plugins/code_editor.py
import sys

from PyQt5.QtCore import QUrl
from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5 import QtWidgets
from pluginsmanager.plugins_gui.plugins import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineFullScreenRequest, QWebEngineView, QWebEngineProfile, QWebEngineSettings
import sys
import json

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QShortcut
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSlot

import os
from typing import List

import chess
import chess.svg

from IPython.display import display
from typing_extensions import Annotated

import sys
import os
import base64
import json
import time
from pathlib import Path

import aiohttp
import requests
import asyncio
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, \
    QStatusBar, QCheckBox
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QDialog

import pyttsx3
import speech_recognition as sr
# from xf_voice.t1_record import my_record
# from xf_voice.sdk_2text import XF_text
# from xf_voice.t4tospeech import speak1
# from xf_voice.t5txt2voice import tospeech
from pluginsmanager.plugins_gui.plugins.xf_voice.t2totxt import listen


made_move = False


class TextToSpeechThread(QThread, QObject):
    sin_out = pyqtSignal(str)

    def __init__(self, obj, parent=None):
        # super().__init__()
        QThread.__init__(self, parent)
        QObject.__init__(self, parent)
        self.obj = obj
        self.engine = pyttsx3.init()
        # rate = self.engine.getProperty('rate')  # 设置语速
        # self.engine.setProperty('rate', rate - 50)

    def Threading_topo(self):
        # 处理耗时操作
        if self.obj.voice_text:
            # 播放文字语音  百度
            # tospeech(self.obj.voice_text)
            # 播放文字语音   系统  pyttsx3
            self.engine.say(self.obj.voice_text)
            self.engine.runAndWait()
            # 播放文字语音  讯飞
            # print(self.obj.voice_text)
            # text_to_voice(self.obj.voice_text)
            # playsound('C:\\fastapi\\aisns\\PyTalk\\my02.wav')

    def run(self):
        # self.engine = pyttsx3.init()
        rate = self.engine.getProperty('rate')  # 设置语速
        print("rate:",rate)
        # self.engine.setProperty('rate', rate - 50)
        self.engine.setProperty('rate', 150)
        self.sin_out.emit("...开始播放语音...")
        time.sleep(1)
        self.Threading_topo()
        time.sleep(1)
        self.sin_out.emit("...结束播放语音...")


class PrintTextThread(QThread, QObject):
    sin_print = pyqtSignal(str)

    def __init__(self, obj, parent=None):
        # super().__init__()
        QThread.__init__(self, parent)
        QObject.__init__(self, parent)
        self.obj = obj

    def Threading_topo(self):
        # 处理耗时操作
        if len(self.obj.print_text) > 0:
            for i in self.obj.print_text:
                self.obj.chatLog.insertPlainText(i)
                time.sleep(0.2)
                # if i[-1] in [",", ".", "?", "!", "，", "。", "？"]:
                #     self.obj.chatLog.insertPlainText(self.obj.print_text)
                #     self.obj.update()
                #     self.obj.repaint()
        self.obj.chatLog.append("")

    def run(self):
        self.sin_print.emit("...开始输出文字...")
        time.sleep(1)
        self.Threading_topo()
        self.sin_print.emit("...结束输出文字...")


class GetVoiceThread(QThread, QObject):
    sin_voice = pyqtSignal(str)
    sin_button = pyqtSignal(str)
    sin_msg = pyqtSignal(str)

    def __init__(self, obj, parent=None):
        # super().__init__()
        QThread.__init__(self, parent)
        QObject.__init__(self, parent)
        self.obj = obj
        self.rate = 16000

    def Threading_topo(self):
        # 处理耗时操作
        r = sr.Recognizer()
        with sr.Microphone(sample_rate=self.rate) as source:
            self.sin_voice.emit("...开始录音,请说话...")
            self.sin_button.emit("请说话")
            print('please say something')
            try:
                audio = r.listen(source, timeout=2)
            except Exception as e:
                print(e)
        # text = r.recognize_google(audio, language='zh-CN')
        # print("text-->",text)
        with open('my01.wav', 'wb') as f:
            try:
                f.write(audio.get_wav_data())
            except Exception as e:
                print(e)
        self.sin_button.emit("录音完成")
        self.sin_voice.emit("...开始转文字...")
        message = ""
        # 语音转文字  讯飞
        # if os.path.exists("my01.wav") and os.path.getsize("my01.wav")>0:
        #     message = XF_text("my01.wav", 16000)
        # 语音转文字 百度
        if os.path.exists("my01.wav") and os.path.getsize("my01.wav") > 0:
            message = listen()

        self.sin_voice.emit("...结束转文字...")
        self.sin_button.emit("文字")
        self.sin_msg.emit(message)

    def run(self):
        self.sin_voice.emit("...开始录音...")
        self.Threading_topo()
        # time.sleep(1)
        self.sin_voice.emit("...结束录音...")


class GetRequestThread(QThread, QObject):
    sin_answer = pyqtSignal(str)
    sin_end = pyqtSignal()

    def __init__(self, obj, parent=None):
        QThread.__init__(self, parent)
        QObject.__init__(self, parent)
        self.obj = obj

    def Threading_topo(self):
        text_list = []
        # url = "http://172.16.206.170:7861/chat/chat?user_id=admin"
        url = "http://61.241.103.48:8000/v1/chat/completions"#nim
        # url = "http://61.241.103.103:17861/chat/chat?user_id=admin"#Yi-34B

        databak = {
            "query": self.obj.question,
            "conversation_id": "",
            "history_len": -1,
            "history": [
            ],
            "stream": True,
            "model_name": "Yi-34B-Chat",  # "chatglm2-6b",  "Yi-34B-Chat",
            "temperature": 0.7,
            "max_tokens": 500,
            "prompt_name": "default"
        }

        data = {
            "model": "chatglm3-6b",
            "messages": [{"role": "user", "content": f"{self.obj.question}"}],
            "max_tokens": 516,
            "top_p": 1,
            "n": 1,
            "stream": True,
            "stop": "string",
            "frequency_penalty": 0.0
        }

        headers = {'Content-Type': 'application/json', "encodings": "utf-8"}
        try:
            response = requests.post(url, json=data, headers=headers, stream=True)
            print(response.status_code)
            # response.raise_for_status()  # 如果响应状态码不是200，引发HTTPError异常
            for i in response.iter_lines():
                if i:
                    text = i.decode('utf-8')
                    decoded_data = json.loads(text.replace("data:", "").strip(""))
                    # text = decoded_data['text']
                    text = decoded_data['choices'][0].get('delta', {}).get('content', '')
                    if self.obj.use_voice == True:
                        text_list.append(text)
                    else:
                        self.obj.chatLog.insertPlainText(text)
            self.obj.answer_list = text_list
        except Exception as e:
            print(f"请求发生错误： {e}")
            self.sin_answer.emit("远程服务器网络异常...")
            self.obj.answer_list = text_list

    def run(self):
        self.sin_answer.emit("...开始连接...")
        self.Threading_topo()
        self.sin_answer.emit("...结束对话...")
        self.sin_end.emit()


class DigitalHuman(QWidget,PluginInterface):
    def __init__(self, content=""):
        super().__init__()
        # Initialize the board.
        self.board = chess.Board()
        self.parent=None


        # Keep track of whether a move has been made.

        # 初始化用户界面

    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局

        self.setWindowTitle("聊天中:...")
        self.setGeometry(100, 100, 380, 680)
        self.base_path = Path(__file__).resolve().parent
        # 主布局分为两部分
        mainLayout = QVBoxLayout()

        # GIF 动画部分使用 QWebEngineView
        self.gifView = QWebEngineView()
        self.gifView.setObjectName("digital_human")
        # self.setGif("C:\\fastapi\\aisns\\PyTalk\\images\\boyin29.gif")  # 替换为你的 GIF 文件的绝对路径
        self.setGif("images/boyin29.gif")
        # self.setGif(os.path.join(self.base_path, "images", "boyin29.gif"))

        # 聊天对话框部分
        self.chatLog = QTextEdit()
        self.chatLog.setReadOnly(True)
        chatInputLayout = QHBoxLayout()
        self.chatInput = QLineEdit()
        self.sendButton = QPushButton("发送")
        self.sendButton.clicked.connect(self.sendMessage)
        self.checkButton = QPushButton("文字")
        self.checkButton.clicked.connect(self.on_checkbutton_clicked)

        self.checkbox = QCheckBox('语音播报', self)
        self.checkbox.stateChanged.connect(self.checkbox_changed)
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("状态栏...")

        chatInputLayout.addWidget(self.chatInput)
        chatInputLayout.addWidget(self.sendButton)
        chatInputLayout.addWidget(self.checkButton)

        checkInputLayout = QVBoxLayout()
        checkInputLayout.addWidget(self.checkbox)

        # 将组件添加到主布局
        mainLayout.addWidget(self.gifView, 1)
        mainLayout.addWidget(self.chatLog, 2)
        mainLayout.addLayout(chatInputLayout)
        mainLayout.addLayout(checkInputLayout)
        mainLayout.addWidget(self.status_bar)

        self.setLayout(mainLayout)

        self.use_voice = False

        self.voice_text = ""
        self.speech_thread = TextToSpeechThread(self, None)
        self.speech_thread.sin_out.connect(self.show_status_text)
        self.print_text = []
        self.print_thread = PrintTextThread(self, None)
        self.print_thread.sin_print.connect(self.show_status_text)
        self.record_thread = GetVoiceThread(self, None)
        self.record_thread.sin_voice.connect(self.show_status_text)
        self.record_thread.sin_button.connect(self.show_button_text)
        self.record_thread.sin_msg.connect(self.show_msg_text)
        self.answer_list = []
        self.question = ""
        self.request_thread = GetRequestThread(self, None)
        self.request_thread.sin_answer.connect(self.show_reqest_text)
        self.request_thread.sin_end.connect(self.print_and_speech)

    def handle_send_message(self, *args, **kwagrs):
        parent=args[0]
        message = args[1]
        if parent.__class__.__name__=="TaskPage":
            self.parent=parent
            parent.system_role_prompt = """
You are a chess player.
You are playing against another player.
You communicate your move using universal chess interface language.
You should ensure you are making legal moves.
Do not apologize for making illegal moves.
            """
            print("TaskPage")
            print("sending message:",message)


            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "digital_human")




            return message
        elif parent.__class__.__name__=="MessageBox":
            self.parent=parent
            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            Do not apologize for making illegal moves.
                        """
            print("MessageBox")
            print("sending message:",message)
            the_move_desc,the_svg_board,the_txt_board=self.make_move(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")


            return message


    def handle_received_message(self, *args, **kwagrs):
        parent = args[0]
        message = args[1]
        if parent.__class__.__name__=="TaskPage":
            self.parent = parent
            print("TaskPage")
            print("sending message:", message)

            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            You do not need to consider whether it is legal of the move made by another player.
            You can only select move from the possible moves.
                        """


            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "digital_human")


            return message

        elif parent.__class__.__name__ == "MessageBox":
            self.parent = parent
            print("MessageBox")
            print("receiveing message:", message)

            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            You do not need to consider whether it is legal of the move made by another player.
            You can only select move from the possible moves.
                        """

            the_move_desc, the_svg_board, the_txt_board = self.make_move_by_ai(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")

            return the_move_desc


    def close_tab(self):
        """向文本编辑器中添加 'Hello World2'"""
        tab = self.parent().parent()
        if tab:
            # 获取并打印父控件的类型
            print(f"父控件类型是: {type(tab).__name__}")
            current_index = tab.currentIndex()  # 获取当前选中的 Tab 的索引
            if current_index != -1:  # 确保有 Tab 被选中
                # 获取当前 Tab 对应的 Widget
                tab_widget = tab.widget(current_index)
                # 使用 deleteLater() 方法安全地删除该 Widget
                tab_widget.deleteLater()
                tab.removeTab(current_index)  # 移除当前选中的 Tab
        else:
            print("没有父控件。")

    def save_file(self):
        """将编辑器中的文本保存到 coding/mindmap.md"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.md")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息

    def preview_file(self):
        """保存文件并在浏览器中打开"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.html")
        html_txt_head="""
        <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta http-equiv="X-UA-Compatible"content="IE=edge"/><meta name="viewport"content="width=device-width, initial-scale=1.0"/><title>Markmap</title><style>svg.markmap{width:100%;height:100vh}</style><script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script></head><body><div class="markmap"><script type="text/template">
        """
        html_txt_tail="""
        </script></div></body></html>
        """
        html_file_content=html_txt_head+self.editor.toPlainText()+html_txt_tail

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(html_file_content)  # 将文本写入文件


        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件

    @pyqtSlot()
    def ai_play(self):
        command = self.text_edit.toPlainText()
        # self.text_edit.clear()
        # Process the command to extract the chess move
        chess_command = command.strip()
        point = self.extract_point(command)

        # Call JavaScript functions in the web page
        self.chess_webview.page().runJavaScript(f"send_msg('{chess_command}');")
        # self.browser.page().runJavaScript(f"make_move('{chess_command}', {json.dumps(point)});")

    def extract_point(self, command):
        # Here we assume the command is in the format: "马8进7(0827)"
        # Extract the points from the command
        if '(' in command and ')' in command:
            point_str = command[command.index('(') + 1:command.index(')')]
            start = [int(point_str[0]), int(point_str[1])]
            end = [int(point_str[2]), int(point_str[3])]
            return [start, end]
        return []



    # 定义一个槽函数，用于处理线程完成后的操作
    def show_status_text(self, text):
        self.status_bar.showMessage(text)
        print(text)

    def show_button_text(self, text):
        self.checkButton.setText(text)
        print(text)

    def show_msg_text(self, text):
        self.chatInput.setText(text)
        print(text)

    def show_reqest_text(self, text):
        self.status_bar.showMessage(text)
        print(text)

    def print_and_speech(self):
        if self.use_voice:
            if (len(self.answer_list)) > 0:
                self.voice_text = "".join(self.answer_list)
                self.speech_thread.start()

                self.print_text = self.answer_list
                self.print_thread.start()

    def checkbox_changed(self, state):
        if state == 2:
            self.use_voice = True
            print('复选框已选中')
        else:
            self.use_voice = False
            print('复选框未选中')

    def setGif(self, gifPath):
        # 将 GIF 文件读取为 Base64 编码的字符串
        print(gifPath)
        with open(gifPath, "rb") as imageFile:
            gifBase64 = base64.b64encode(imageFile.read()).decode('utf-8')

        gifBase64 = ""  # 通过 HTML 显示 GIF
        htmlContent = f"""

        <img src="data:image/gif;base64,{gifBase64}" style="width: 100%; height: auto;">

        """
        htmlContent = f"""<html><body>cjrok{gifBase64}</body></html>"""
        # self.gifView.setHtml(htmlContent)
        print(htmlContent)
        gifBase64 = "aa<img src='a.gif'>bb"
        # self.gifView.page().runJavaScript('document.body.innerHTML += "' + gifBase64 + '"')
        # self.gifView.load(QUrl.fromLocalFile("C:\\fastapi\\aisns\\PyTalk\\gifchat4v3.html"))
        # base_path = Path(__file__).resolve().parent
        # self.gifView.load(QUrl.fromLocalFile(os.path.join(self.base_path, "gifchat4v3.html")))
        # print(QUrl.fromLocalFile("\\gifchat4v3.html"))
        try:
            # 检查是否在 PyInstaller 打包的环境中运行
            # if hasattr(sys, '_MEIPASS'):
            #     # 在打包环境中运行
            #     file_path = sys._MEIPASS + "/images/gifchat4v3.html"
            # else:
            #     # 在非打包环境中运行
            #     self.gifView.load(QUrl.fromLocalFile("/images/gifchat4v3.html"))
            self.gifView.load(QUrl.fromLocalFile("/images/gifchat4v3.html"))
        except Exception as e:
            print(e)

    def sendMessage(self):
        message = self.chatInput.text()
        text_list = []
        if message:
            self.chatLog.append("You: " + message)
            self.chatInput.clear()
            self.chatLog.append("LLM: ")
            # time.sleep(2)
            self.update()
            self.repaint()

            # self.update()
            self.question = message
            self.request_thread.start()
            # self.request_thread.wait()

    def on_checkbutton_clicked(self):
        if self.checkButton.text() == '文字':
            self.chatInput.clear()
            self.checkButton.setText('语音')
            if os.path.exists("my01.wav"):
                os.remove("my01.wav")
            # self.update()
            self.record_thread.start()
            # self.update()
        else:
            self.checkButton.setText('文字')

