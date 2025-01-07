# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_MessageWidget.ui'
#
# Created: Tue Jan 22 07:03:54 2008
#      by: PyQt5 UI code generator 5.15.4
#
# WARNING! All changes made in this file will be lost!
import os
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QUrl, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QCheckBox, QLabel, QSplitter, QTabWidget, QVBoxLayout, QWidget, QMessageBox, QLineEdit
from qtpy.QtCore import Qt, QMetaObject, Signal, Slot, QEvent
from PyQt5.QtWebChannel import QWebChannel

from ChatListLabel import ChatListLabel
from i18n import lt
from ChatList import ChatList


class MessageHandler(QWidget):
    on_message = pyqtSignal(str)
    on_message_checked = pyqtSignal(int, str)
    on_edit_content_message = pyqtSignal(str, str)
    on_message_file_clicked = pyqtSignal(str)
    on_message_open_link = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok"

    def PyQt52WebValue(self):
        return self.theinnervalue

    @pyqtSlot(str, result=str)
    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    @pyqtSlot(int, str, result=str)
    def check_message(self, i, status):
        print("i:", i)
        print("status", status)
        self.on_message_checked.emit(i, status)

    @pyqtSlot(str, str, result=str)
    def edit_content_message(self, code_type, text):
        print("codetype:", code_type)
        print("text:", text)
        self.on_edit_content_message.emit(code_type, text)

    @pyqtSlot(str, result=str)
    def file_clicked_message(self, file_path):
        print("file_path:", file_path)
        self.on_message_file_clicked.emit(file_path)

    @pyqtSlot(str, result=str)
    def open_link_message(self, url):
        print("url:", url)
        self.on_message_open_link.emit(url)

    def pass_message(self, messsage):
        self.on_message.emit(messsage)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)


class Ui_MessageWidget(object):
    def setupUi(self, MessageWidget):
        MessageWidget.setObjectName("MessageWidget")
        MessageWidget.resize(
            QtCore.QSize(QtCore.QRect(0, 0, 800, 600).size()).expandedTo(MessageWidget.minimumSizeHint()))
        MessageWidget.setContentsMargins(0, 0, 0, 0)  # 不留间隙

        self.vboxlayout = QtWidgets.QVBoxLayout(MessageWidget)
        self.vboxlayout.setObjectName("vboxlayout")
        self.vboxlayout.setContentsMargins(0, 0, 0, 0)  # 不留间隙

        # # 添加标签到布局中
        # title_label = QLabel("聊天对象：" + self.name, MessageWidget)
        # title_label.setStyleSheet("color: #146ebe;font-weight:bold")
        # title_label.setContentsMargins(0, 0, 0, 0)  # 不留间隙
        # title_label.setFixedHeight(30)  # 影响间隙
        #
        #
        # self.vboxlayout.addWidget(title_label)

        # 添加标签到布局中
        self.hboxlayoutlabel = QtWidgets.QHBoxLayout()

        spacerItem_label_left = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                                      QtWidgets.QSizePolicy.Minimum)
        self.hboxlayoutlabel.addItem(spacerItem_label_left)  # 通过留空来居中

        self.title_label = QLabel("聊天对象：" + self.name, MessageWidget)
        self.title_label.setStyleSheet("color: #146ebe;font-weight:bold")
        self.title_label.setContentsMargins(0, 0, 0, 0)  # 不留间隙
        self.title_label.setFixedHeight(30)  # 影响间隙

        self.title_label.setStyleSheet("color: #146ebe;font-weight:bold")
        self.title_label.setFixedHeight(30)  # 影响间隙
        self.title_label.setContentsMargins(0, 0, 0, 0)  # 不留间隙
        self.hboxlayoutlabel.addWidget(self.title_label)

        spacerItem_label_right = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                                       QtWidgets.QSizePolicy.Minimum)
        self.hboxlayoutlabel.addItem(spacerItem_label_right)  # 通过留空来居中

        self.vboxlayout.addLayout(self.hboxlayoutlabel)

        # self.messageBrowser = QtWidgets.QTextBrowser(MessageWidget)
        # self.messageBrowser.setObjectName("messageBrowser")
        # self.vboxlayout.addWidget(self.messageBrowser)

        # 使用 QSplitter 来管理 self.frame 和 self.tabWidget
        self.splitter = QSplitter(Qt.Horizontal, MessageWidget)

        # self.messageBrowser = QtWidgets.QTextBrowser(TaskWidget)
        # self.messageBrowser = QtWidgets.QTextBrowser(MessageWidget)
        self.messageBrowser = QWebEngineView()
        self.messageBrowser.setObjectName("messageBrowser")

        self.frame = QtWidgets.QFrame(self.splitter)
        self.frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;}")
        self.frame_layout = QtWidgets.QVBoxLayout(self.frame)
        self.frame_layout.addWidget(self.messageBrowser)

        # 创建 QTabWidget 控件及其页签，设置页签在底部
        self.tabWidget = QTabWidget(self.splitter)
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.South)

        self.tab_output = QtWidgets.QWidget()
        self.tab_output.setObjectName("tab_output")
        self.tabLayout_output = QtWidgets.QVBoxLayout(self.tab_output)
        self.tabLayout_output.setContentsMargins(0, 0, 0, 0)
        self.output_webview = QWebEngineView(self.tab_output)
        self.tabLayout_output.addWidget(self.output_webview)
        self.tabWidget.addTab(self.tab_output, "输出")

        self.tab_log = QtWidgets.QWidget()
        self.tab_log.setObjectName("tab_log")
        self.tabLayout_log = QVBoxLayout(self.tab_log)
        self.tabLayout_log.setContentsMargins(0, 0, 0, 0)
        self.textEdit_log = QtWidgets.QTextEdit(self.tab_log)
        self.textEdit_log.setReadOnly(True)
        self.tabLayout_log.addWidget(self.textEdit_log)
        self.tabWidget.addTab(self.tab_log, "日志")

        # Create search input
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("关键词+回车搜索，空+回车复原")
        textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")

        tab_widget = QWidget()
        self.tab_chat_list = ChatList(self, self.ai_chat_cfg)
        self.tab_chat_list.setObjectName("chat_list")
        self.tabLayout_chat_list = QVBoxLayout(tab_widget)
        self.tabLayout_chat_list.addWidget(textEdit)
        self.tabLayout_chat_list.addWidget(self.tab_chat_list)
        self.tabLayout_chat_list.setContentsMargins(5, 5, 5, 5)
        # Connect returnPressed signal to search function
        textEdit.returnPressed.connect(lambda: self.tab_chat_list.search(textEdit.text()))

        self.tabWidget.addTab(tab_widget, "聊天历史")

        # Create search input
        textEdit_label = QLineEdit()
        textEdit_label.setPlaceholderText("关键词+回车搜索，空+回车复原")
        textEdit_label.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        tab_widget_label = QWidget()
        self.tab_chat_list_label = ChatListLabel(self, self.ai_chat_cfg)
        self.tab_chat_list_label.setObjectName("chat_list_label")
        self.tabLayout_chat_list_label = QVBoxLayout(tab_widget_label)
        self.tabLayout_chat_list_label.addWidget(textEdit_label)
        self.tabLayout_chat_list_label.addWidget(self.tab_chat_list_label)
        self.tabLayout_chat_list_label.setContentsMargins(5, 5, 5, 5)
        # Connect returnPressed signal to search function
        textEdit_label.returnPressed.connect(lambda: self.tab_chat_list_label.search(textEdit_label.text()))
        self.tabWidget.addTab(tab_widget_label, "聊天标签")

        self.splitter.setSizes([1, ])  # 设置初始状态不显示输出窗口

        self.vboxlayout.addWidget(self.splitter)

        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)

        self.fontButton = QtWidgets.QPushButton(MessageWidget)
        self.fontButton.setIcon(QtGui.QIcon("images/face.png"))
        self.fontButton.setObjectName("fontButton")
        self.hboxlayout.addWidget(self.fontButton)

        self.videoButton = QtWidgets.QPushButton(MessageWidget)
        self.videoButton.setIcon(QtGui.QIcon("images/attachment.png"))
        self.videoButton.setObjectName("videoButton")
        self.hboxlayout.addWidget(self.videoButton)

        self.humantakeoverCheckBox = QCheckBox("人类接管聊天")
        self.humantakeoverCheckBox.setObjectName("humantakeoverCheckBox")
        self.hboxlayout.addWidget(self.humantakeoverCheckBox)

        # 添加 "输出" QCheckBox
        self.output_checkbox = QCheckBox(lt("Side Pane|边窗"), MessageWidget)
        self.output_checkbox.stateChanged.connect(self.toggle_output_checkbox)
        self.output_checkbox.setChecked(False)
        self.hboxlayout.addWidget(self.output_checkbox)

        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem1)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.hboxlayout1 = QtWidgets.QHBoxLayout()
        self.hboxlayout1.setObjectName("hboxlayout1")

        # self.messageEdit = QtWidgets.QLineEdit(MessageWidget)

        self.messageEdit = QtWidgets.QTextEdit(MessageWidget)
        self.messageEdit.setAcceptRichText(False)  # 设置为不接受富文本，否则格式特别是背景总数很混乱
        self.messageEdit.setFixedHeight(45)  # 假设每行高度为20像素
        self.messageEdit.setStyleSheet("""
            QTextEdit {
                border-radius: 2px; /* 设置圆角 */
                border: 1px solid #c0c0c0; /* 设置边框 */
            }
            QTextEdit:focus {
                border-color: #61addf; /* 设置焦点时的边框颜色 */
            }
        """)

        self.messageEdit.setObjectName("messageEdit")
        # 连接 textChanged 信号到槽函数
        self.messageEdit.textChanged.connect(self.adjustHeight)
        self.hboxlayout1.addWidget(self.messageEdit)

        self.sendButton = QtWidgets.QPushButton(MessageWidget)
        self.sendButton.setIcon(QtGui.QIcon("images/sendmessage.png"))
        self.sendButton.setObjectName("sendButton")
        self.hboxlayout1.addWidget(self.sendButton)
        self.vboxlayout.addLayout(self.hboxlayout1)

        self.retranslateUi(MessageWidget)
        QtCore.QMetaObject.connectSlotsByName(MessageWidget)

    def adjustHeight(self):
        line_height = 20  # 每行高度为20像素
        min_height = 40  # 最小高度为40像素
        max_height = 200  # 最大高度为90像素
        print("in adjustHeight")

        # 计算文本行数
        document = self.messageEdit.document()
        document_height = document.size().height()
        lines = int(document_height / line_height)

        # 计算新的高度
        new_height = max(min_height, min(max_height, lines * line_height))

        # 设置新的高度
        self.messageEdit.setFixedHeight(new_height + 5)

    def retranslateUi(self, MessageWidget):
        MessageWidget.setWindowTitle(QtCore.QCoreApplication.translate("MessageWidget", "Message", None))
        # self.messageBrowser.setHtml(QtCore.QCoreApplication.translate("MessageWidget", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        # "p, li { white-space: pre-wrap; }\n"
        # "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
        # "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; color:#00008b;\">[14:51] Mauryson :</span><span style=\" color:#00008b;\"> </span><span style=\" color:#000000;\">Salut</span></p>\n"
        # "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; color:#000000;\"><span style=\" font-weight:600; font-style:italic; color:#8b0000;\">[14:52] Natim :</span> Coucou</p></body></html>", None))
        # self.messageBrowser.setHtml(QtCore.QCoreApplication.translate("MessageWidget", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        #                                                      "p, li { white-space: pre-wrap; }\n"
        #                                                      "</style></head><body style=\" font-family:\'Microsoft YaHei\'; font-size:14pt; font-weight:400; font-style:normal;\">"
        #                                                      "</body></html>"))

        file_path = os.path.join(Path(__file__).resolve().parent.parent, "scripts", "aichatmessagepage.html")
        # file_path = os.path.join(Path(__file__).resolve().parent.parent, "scripts", "index3.html")
        print(file_path)
        url_string = QUrl.fromLocalFile(file_path)
        # url_string = urllib.request.pathname2url(os.path.join(Path(__file__).resolve().parent.parent, "scripts", "aichatmessagepage.html"))
        print("transform")
        print(url_string)

        # self.output_webview.page().load(mind_url_string)
        print("url_string:", url_string)

        self.messageBrowser.page().load(url_string)
        global channel
        global message_handler
        channel = QWebChannel()
        message_handler = MessageHandler()
        self.message_handler = message_handler
        self.channel = channel
        channel.registerObject("message_handler", message_handler)

        # self.messageBrowser.page().setWebChannel(channel)
        self.messageBrowser.page().setWebChannel(channel)

        self.fontButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "表情", None))
        self.videoButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "附件", None))
        self.sendButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "发送", None))
        # self.sendButton.setShortcut(QtCore.QCoreApplication.translate("MessageWidget", "Return", None))
        self.sendButton.setShortcut(QtGui.QKeySequence(Qt.ControlModifier + Qt.Key_Return))
