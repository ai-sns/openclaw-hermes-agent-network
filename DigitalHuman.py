import sys
import os
import base64
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout,QTextEdit, QLineEdit, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QDialog
from pathlib import  Path
class ChatApp(QDialog,QWidget):
    def __init__(self, parent=None):
        super(ChatApp, self).__init__(parent)

        self.setWindowTitle("聊天中...")
        self.setGeometry(100, 100, 380, 680)

        # 主布局分为两部分
        mainLayout = QVBoxLayout()

        # GIF 动画部分使用 QWebEngineView
        self.gifView = QWebEngineView()
        gif_path = os.path.join(Path(__file__).resolve().parent,"images","boyin29.gif")
        self.setGif(gif_path)  # 替换为你的 GIF 文件的绝对路径

        # 聊天对话框部分
        self.chatLog = QTextEdit()
        self.chatLog.setReadOnly(True)
        chatInputLayout = QHBoxLayout()
        self.chatInput = QLineEdit()
        self.sendButton = QPushButton("发送")
        self.sendButton.clicked.connect(self.sendMessage)

        chatInputLayout.addWidget(self.chatInput)
        chatInputLayout.addWidget(self.sendButton)

        # 将组件添加到主布局
        mainLayout.addWidget(self.gifView, 1)
        mainLayout.addWidget(self.chatLog, 2)
        mainLayout.addLayout(chatInputLayout)

        self.setLayout(mainLayout)

    def setGif(self, gifPath):
        # 将 GIF 文件读取为 Base64 编码的字符串
        with open(gifPath, "rb") as imageFile:
            gifBase64 = base64.b64encode(imageFile.read()).decode('utf-8')

        gifBase64=""# 通过 HTML 显示 GIF
        htmlContent = f"""

        <img src="data:image/gif;base64,{gifBase64}" style="width: 100%; height: auto;">

        """
        htmlContent=f"""<html><body>cjrok{gifBase64}</body></html>"""
        #self.gifView.setHtml(htmlContent)
        print(htmlContent)
        gifBase64="aa<img src='a.gif'>bb"
        #self.gifView.page().runJavaScript('document.body.innerHTML += "' + gifBase64 + '"')
        html_path = gif_path = os.path.join(Path(__file__).resolve().parent,"images","digitalhumanhrx.html")
        self.gifView.load(QUrl.fromLocalFile(html_path))

    def sendMessage(self):
        message = self.chatInput.text()
        if message:
            self.chatLog.append("You: " + message)
            self.chatInput.clear()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatApp()
    window.show()
    sys.exit(app.exec_())
