# plugins/code_editor.py
import sys

from PyQt5.QtCore import QUrl
from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QMessageBox
from PyQt5 import QtWidgets
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineFullScreenRequest, QWebEngineView, QWebEngineProfile, QWebEngineSettings
import sys
import json

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QShortcut
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineFullScreenRequest, QWebEngineView, QWebEngineProfile, QWebEngineSettings

from PyQt5.QtCore import QUrl, pyqtSlot

import chess
import chess.svg

from IPython.display import display
from typing_extensions import Annotated


class MessageHandler(QWidget):
    on_message_init = pyqtSignal(str)#发送给html页面的消息，让html页面初始化
    on_message_receive = pyqtSignal(str)#发送给html页面的消息，告诉html页面获取到消息
    on_message_send = pyqtSignal(str)#发送给chinese_chess插件的消息，走好棋子，要向对手发送消息

    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok"

    def PyQt52WebValue(self):
        return self.theinnervalue

    @pyqtSlot(str, result=str)
    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    @pyqtSlot(str,result=str)
    def send_message(self,message):
        print("in send_message...aaaaa....")
        print(message)
        self.on_message_send.emit(message)

    @pyqtSlot(str,result=str)
    def sendcjrok(self,message):
        print("incjrok function:::::::::")
        print(message)
        # self.on_message_send.emit(message)

    @pyqtSlot(str, str, result=str)
    def edit_content_message(self,code_type,text):
        print("codetype:",code_type)
        print("text:",text)
        self.on_edit_content_message.emit(code_type,text)

    @pyqtSlot(str, result=str)
    def file_clicked_message(self,file_path):
        print("file_path:",file_path)
        self.on_message_file_clicked.emit(file_path)

    @pyqtSlot(str, result=str)
    def open_link_message(self, url):
        print("url:", url)
        self.on_message_open_link.emit(url)



    def pass_message(self, messsage,type_flag=1):
        print("passmessage")
        if type_flag==1:
            self.on_message_receive.emit(messsage)
        else:
            self.on_message_init.emit(messsage)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)


class Main(QWidget, PluginInterface):
    def __init__(self, parent, plugin_cfg, content=""):
        super().__init__()
        # Initialize the board.
        self.parent = parent
        self.plugin_cfg = plugin_cfg
        # 初始化用户界面


    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局

        chess_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(chess_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        chess_webview = QWebEngineView(chess_widget)
        chess_webview.setObjectName("chinese_chess")
        chess_webview.setUrl(QUrl("file:///scripts/Chess-master/index.html"))
        global channel
        global message_handler
        channel = QWebChannel()
        message_handler = MessageHandler()
        self.message_handler = message_handler
        self.channel = channel
        channel.registerObject("message_handler", message_handler)

        # self.messageBrowser.page().setWebChannel(channel)
        chess_webview.page().setWebChannel(channel)

        message_handler.on_message_send.connect(self.send_message)


        self.chess_webview=chess_webview
        layout.addWidget(chess_webview)

        # Create QTextEdit
        self.text_edit = QTextEdit(self)
        self.text_edit.setFixedHeight(80)
        self.text_edit.setPlainText("车9进1(0908)")
        layout.addWidget(self.text_edit)

        # 创建按钮的水平布局
        button_layout = QHBoxLayout()

        # 创建添加按钮
        hello_button = QPushButton("关闭")
        hello_button.clicked.connect(self.close_tab)  # 连接按钮点击事件到添加函数
        button_layout.addWidget(hello_button)

        # 创建保存按钮
        save_button = QPushButton("AI代下")
        save_button.clicked.connect(self.ai_play)  # 连接保存事件
        button_layout.addWidget(save_button)

        # 创建预览按钮
        preview_button = QPushButton("优化我的AI算法")
        preview_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(preview_button)

        # 创建预览按钮
        import_button = QPushButton("导入算法")
        import_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(import_button)

        # 创建预览按钮
        reset_button = QPushButton("重置算法")
        reset_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(reset_button)

        # 将按钮布局添加到主布局
        layout.addLayout(button_layout)



        # 设置窗口布局
        self.setLayout(layout)
        # 设置窗口标题
        self.setWindowTitle("中国象棋")
        # 设置窗口大小
        self.resize(600, 400)

    def handle_send_message(self, *args, **kwagrs):
        parent = args[0]
        message = args[1]
        if parent.__class__.__name__ == "TaskPage":
            self.parent = parent
            parent.system_role_prompt = """
You are a Chinese chess player.
You are playing against another player.
            """
            print("TaskPage")
            print("sending message:", message)


            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chinese_chess")



            return message
        elif parent.__class__.__name__ == "MessageBox":
            self.parent = parent
            parent.system_role_prompt = """
You are a Chinese chess player.
You are playing against another player.
                        """
            print("MessageBox")
            print("sending message:", message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chinese_chess")

            return message

    def handle_previous_to_send_im_b(self, *args, **kwagrs):
            parent = args[0]
            message = args[1]
            if parent.__class__.__name__ == "TaskPage":
                self.parent = parent
                parent.system_role_prompt = """
    You are a Chinese chess player.
    You are playing against another player.
                """
                print("TaskPage")
                print("sending message:", message)

                tabs = parent.tabWidget
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")

                return message
            elif parent.__class__.__name__ == "MessageBox":
                self.parent = parent
                parent.system_role_prompt = """
    You are a Chinese chess player.
    You are playing against another player.
                            """
                print("MessageBox")
                print("sending message:", message)

                tabs = parent.tabWidget
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")

                return message

    def handle_received_message(self, *args, **kwagrs):
        parent = args[0]
        message = args[1]
        if parent.__class__.__name__ == "TaskPage":
            self.parent = parent
            print("TaskPage")
            print("sending message:", message)

            parent.system_role_prompt = """
You are a Chinese chess player.
You are playing against another player.
                        """


            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chinese_chess")


            return message

        elif parent.__class__.__name__ == "MessageBox":
            self.parent = parent
            print("MessageBox")
            print("receiveing message:", message)

            parent.system_role_prompt = """
You are a Chinese chess player.
You are playing against another player.
                        """


            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chinese_chess")
            self.message_handler.pass_message(message, type_flag=1)  # 初始化



            return message

    def handle_after_send_im_a(self, *args, **kwagrs):
            parent = args[0]
            message = args[1].replace("//中国象棋","")
            if parent.__class__.__name__ == "TaskPage":
                self.parent = parent
                print("TaskPage")
                print("sending message:", message)

                parent.system_role_prompt = """
    You are a Chinese chess player.
    You are playing against another player.
                            """

                tabs = parent.tabWidget
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")

                return message

            elif parent.__class__.__name__ == "MessageBox":
                self.parent = parent
                print("MessageBox")
                print("receiveing message:", message)

                parent.system_role_prompt = """
    You are a Chinese chess player.
    You are playing against another player.
                            """

                tabs = parent.tabWidget
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")
                self.message_handler.pass_message(message, type_flag=1)  # 初始化

                return message

    def handle_after_send_im_b(self, *args, **kwagrs):
        parent = args[0]
        content = args[1]

        if parent.__class__.__name__ == "MessageBox":
            self.parent = parent
            print("MessageBox")
            print("receiveing message:", content)

            tmp_content = content.strip()
            tmp_content = tmp_content.replace(".", "")

            content = "//中国象棋" + tmp_content[-4:]

            return content

    def close_tab(self):
        """向文本编辑器中添加 'Hello World2'"""
        # tab = self.parent().parent()
        tab = self.parent.tabWidget
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
                self.parent.plugin_tool_loaded_list.pop(self.plugin_cfg.name, None)
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
        # self.chess_webview.page().runJavaScript(f"send_msg('{chess_command}');")
        #
        # self.message_handler.pass_message(point)
        self.message_handler.pass_message("start",type_flag=0)#初始化




        # self.browser.page().runJavaScript(f"make_move('{chess_command}', {json.dumps(point)});")

    def extract_point(self, command):
        # Here we assume the command is in the format: "马8进7(0827)"
        # Extract the points from the command
        if '(' in command and ')' in command:
            point_str = command[command.index('(') + 1:command.index(')')]
            # start = [int(point_str[0]), int(point_str[1])]
            # end = [int(point_str[2]), int(point_str[3])]
            # return [start, end]
            return point_str
        return []

    def send_message(self,message):
        print(message)
        if self.parent:
            self.parent.sendMessage("//中国象棋"+message)



