import os
from pathlib import Path

# 获取当前文件的目录
app_directory = Path(__file__).resolve().parent

# 设置工作目录为 app.py 所在的目录
os.chdir(app_directory)

# 验证工作目录
print("当前工作目录:", os.getcwd())

import sys
import datetime
from db.DBFactory import add_AgentCfg, query_AgentCfg_All, update_AgentCfg, delete_AgentCfg
import copy
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QShortcut
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon, QKeySequence, QFont, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QTextEdit,
    QDialog,
    QMessageBox,
    QTreeWidgetItem,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QUrl
from qdarkstyle import LightPalette

# import gifchat
from ui.ui_mainwindow import Ui_MainWindow
from pyqt_explanation_balloon.explanationBalloon import ExplanationBalloon
from AboutDialog import AboutDialog
from ConnectionDialog import ConnectionDialog
from ConnectorThread import ConnectorThread
from MessageBox import MessageBox
from BuddyList import BuddyList
from TaskList import TaskList
from KMList import KMList
from TechList import TechList
from RosterRequest import RosterRequest
from AddBuddyDialog import AddBuddyDialog
from AddGroupDialog import AddGroupDialog

from jabber import STATUS
import asyncio

from qt_material import apply_stylesheet
import qdarkstyle

import qtmodern.styles
import qtmodern.windows
import markdown
import webbrowser

from pluginsmanager import PluginEngine

import argparse

from pluginsmanager import FileSystem

from globals import global_agent_list, global_plugin_list, global_buddy_list
from DigitalHuman import ChatApp
from PyQt5.QtWebEngineWidgets import QWebEngineView

from TaskPage import TaskPage

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QMainWindow, QPushButton, QVBoxLayout
from PyQt5.QtCore import pyqtSlot, Qt, QUrl, QFileInfo, pyqtProperty
from Agent import Agent


class MainWindow(QMainWindow, Ui_MainWindow):
    connectorThread = None

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.window_max_width = 0
        self.window_max_height = 0

        self.setWindowIcon(QIcon("C:\\dev\\ai-sns\\PyTalk\\pytalk\\images\\aisns.png"))
        self.agent_cfg_dialog_list = {}
        self.ai_chat_cfg_dialog_list = {}
        self.human_chat_cfg_dialog_list = {}
        self.km_cfg_dialog_list = {}
        self.km_note_window_list = {}
        self.agent_chat_window_list = {}
        self.multi_agent_chat_window_list = {}
        self.connectorThread_list = {}
        self.connectorThread_human_list = {}
        self.notelist_recent_list = {}
        self.notelist_all_list = {}
        self.tasklist_list = {}
        self.techlist_list = {}
        self.tasklist_group_list = {}
        self.memberlist_group_list = {}
        self.buddylist_list = {}
        self.buddylist_human_list = {}
        self.contactlist_list = {}
        self.contactlist_human_list = {}
        self.kmlist_list = {}
        self.kmlist_list_deleted = {}
        self.get_all_agent()
        self.setupUi(self)  # 调用Ui_MainWindow的函数初始化界面，包括菜单等
        self.note_editor_dialog = None

        self.console = QDialog()
        self.te = QTextEdit(self.console)
        self.te.setReadOnly(True)
        vl = QVBoxLayout()
        vl.addWidget(self.te)
        self.console.setLayout(vl)

        # Set status Offline
        self.statusBox.setCurrentIndex(5)
        self.statusEdit.hide()

        # Set connect
        self.statusBox.currentIndexChanged.connect(self.changeStatus)
        # self.statusEdit.returnPressed.connect(self.changeStatus)

        # Set BuddyList
        # self.BuddyList = BuddyList(self)
        # self.BuddyList2 = BuddyList(self)
        # self.vboxlayout.insertWidget(0, self.BuddyList)

        # self.tabWidget.addTab(self.BuddyList, "聊天")
        # self.tabWidget.addTab(self.BuddyList2, "通讯录")

        global_buddy_list = "self.BuddyList"

        # self.toolBox_AiChat.addItem(self.BuddyList,"Buddy List")
        # self.BuddyList.rename_signal.connect(self.addBuddy)
        # self.ContactList.rename_signal.connect(self.addBuddy)

        # Connection
        # connection = ConnectionDialog(self)
        # self.actionConnection.triggered.connect(connection.exec_)#actionConnection是ui_mainwindow的菜单项，该项触发ConnectionDialog对象的运行
        self.actionConnection.triggered.connect(self.connection_handle)

        self.actionDeconnection.triggered.connect(self.disconnect)
        # connection.configured.connect(self.on_configured)#连接对话框如果连接成功将触发当前Application.py文件中的on_configured函数
        # self.connect(connection, "configured()", self.connection)
        # connection.configured.connect(self.connection)

        # View
        self.actionAdd_a_buddy.triggered.connect(self.addBuddy)
        self.actionAdd_a_group.triggered.connect(self.addGroup)
        self.chatbox = ChatApp(self)
        # self.togglechatbox.triggered.connect(self.chatbox.exec_)
        self.togglechatbox.triggered.connect(self.handletogglechatbox)
        self.actionShow_agent_homepage.triggered.connect(self.showagenthome)
        self.actionShow_ai_homepage.triggered.connect(self.showaihome)
        self.actionShow_human_homepage.triggered.connect(self.showhumanhome)
        self.actionShow_km_homepage.triggered.connect(self.showkmhome)
        self.actionShow_plugin_homepage.triggered.connect(self.showpluginhome)

        # View
        # self.actionAway_buddies.toggled.connect(self.setAway)
        # self.actionOffline_buddies.toggled.connect(self.setOffline)
        # self.actionAway_buddies.triggered.connect(self.setAway)
        # self.actionOffline_buddies.triggered.connect(self.setOffline)
        # # about = AboutDialog(self)

        # Help

        self.actionOffline_buddies.triggered.connect(self.opendochelp)
        self.actionAway_buddies.triggered.connect(self.openwebhelp)
        self.actionConsole.triggered.connect(self.swapConsole)

        # About Dialog
        about = AboutDialog(self)
        # about = ChatApp(self)
        self.actionAbout.triggered.connect(about.exec_)
        self.actionAboutQt.triggered.connect(QApplication.instance().aboutQt)

        # Quit Signal connection
        self.actionQuit.triggered.connect(self.quit)

        self.conversation_pages = QtWidgets.QStackedWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.conversation_pages.sizePolicy().hasHeightForWidth())
        self.conversation_pages.setSizePolicy(sizePolicy)
        self.conversation_pages.setAutoFillBackground(False)
        self.conversation_pages.setObjectName("conversation_pages")

        self.dialogwidge = QDialog()
        self.dialogwidge2 = QtWidgets.QTextBrowser()  # 系统打开时的首界面上的显示的编辑框

        # ai_chat_cfg home
        agent_home = QWebEngineView()
        self.agent_home_frame = QtWidgets.QFrame(self)
        self.agent_home_frame.setContentsMargins(0, 0, 0, 0)
        self.agent_home_frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;margin:0,0,0,0;padding:0,0,0,0}")
        agent_home_frame_layout = QtWidgets.QVBoxLayout(self.agent_home_frame)
        agent_home_frame_layout.addWidget(agent_home)

        # file_path = os.path.join(Path(__file__).resolve().parent, "scripts", "index3.html")
        # print(file_path)
        # url_string = QUrl.fromLocalFile(file_path)

        agent_home.page().load(QUrl("http://www.ai-sns.org/index_agent.html"))
        # agent_home.page().load(QUrl(url_string))
        self.agent_home = agent_home

        # ai home
        ai_home = QWebEngineView()
        self.ai_home_frame = QtWidgets.QFrame(self)
        self.ai_home_frame.setContentsMargins(0, 0, 0, 0)
        self.ai_home_frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;margin:0,0,0,0;padding:0,0,0,0}")
        ai_home_frame_layout = QtWidgets.QVBoxLayout(self.ai_home_frame)
        ai_home_frame_layout.addWidget(ai_home)
        ai_home.page().load(QUrl("http://www.ai-sns.org/index_aichat.html"))

        # human home
        human_home = QWebEngineView()
        self.human_home_frame = QtWidgets.QFrame(self)
        self.human_home_frame.setContentsMargins(0, 0, 0, 0)
        self.human_home_frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;margin:0,0,0,0;padding:0,0,0,0}")
        human_home_frame_layout = QtWidgets.QVBoxLayout(self.human_home_frame)
        human_home_frame_layout.addWidget(human_home)
        human_home.page().load(QUrl("http://www.ai-sns.org/index_humanchat.html"))

        # km home
        km_home = QWebEngineView()
        self.km_home_frame = QtWidgets.QFrame(self)
        self.km_home_frame.setContentsMargins(0, 0, 0, 0)
        self.km_home_frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;margin:0,0,0,0;padding:0,0,0,0}")
        km_home_frame_layout = QtWidgets.QVBoxLayout(self.km_home_frame)
        km_home_frame_layout.addWidget(km_home)
        km_home.page().load(QUrl("http://www.ai-sns.org/index_km.html"))

        # plugin home
        plugin_home = QWebEngineView()
        self.plugin_home_frame = QtWidgets.QFrame(self)
        self.plugin_home_frame.setContentsMargins(0, 0, 0, 0)
        self.plugin_home_frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;margin:0,0,0,0;padding:0,0,0,0}")
        plugin_home_frame_layout = QtWidgets.QVBoxLayout(self.plugin_home_frame)
        plugin_home_frame_layout.addWidget(plugin_home)
        plugin_home.page().load(QUrl("http://www.ai-sns.org/index_plugin.html"))

        # self.dialogwidge2.setStyleSheet("QTextBrowser { padding: 2px; }")
        # self.dialogwidge2.setReadOnly(True)

        # 加载 Markdown 文件
        markdown_file_path = 'readme.md'
        with open(markdown_file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        # 将 Markdown 转换为 HTML
        html_content = markdown.markdown(markdown_content)


        # 添加自定义的 CSS 样式
        html_with_style = f"""
                <html>
                <head>
                    <style>
                        /* 添加自定义的 CSS 样式 */
                        body {{
                            margin-left: 20px;
                            margin-top: 20px;
                            margin-right: 20px;
                            margin-bottom: 20px;                            
                        }}
                    </style>
                </head>
                <body>

                 {html_content}

                </body>
                </html>
            """
        print("html_content:",html_content)
        # 在 QTextEdit 中显示 HTML 内容
        self.dialogwidge2.setHtml(html_with_style)
        self.dialogwidge2.setOpenLinks(False)
        self.dialogwidge2.anchorClicked.connect(self.openLink)

        # self.dialogwidge.setWindowIcon(QIcon("images/mail.png"))
        #
        # self.msg = MessageBox(self.dialogwidge, None, "chenchen@xabber.de", "chenchen")
        # tlayout = QVBoxLayout(self.dialogwidge)
        # tlayout.addWidget(self.msg)
        # # self.dialogwidge.setStyleSheet("border: 2px solid red;")
        #
        # self.dialogwidge.setLayout(tlayout)
        # self.dialogwidge.setWindowTitle(self.dialogwidge.tr("Chat with ") + "chenchen")
        #
        # self.conversation_pages.addWidget(self.dialogwidge)
        #
        self.conversation_pages.addWidget(self.dialogwidge2)
        self.conversation_pages.addWidget(self.agent_home_frame)
        self.conversation_pages.addWidget(self.ai_home_frame)
        self.conversation_pages.addWidget(self.human_home_frame)
        self.conversation_pages.addWidget(self.km_home_frame)
        self.conversation_pages.addWidget(self.plugin_home_frame)

        self.conversation_pages.setCurrentIndex(0)

        self.hlayout.addWidget(self.conversation_pages)  # hlayout在ui_mainwindow.py中定义了
        self.cjr = "cjrok"

        # self.shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        # self.shortcut.activated.connect(self.toggle_search_box)

    # def showMaximized(self):
    #     """重写最大化事件"""
    #     super().showMaximized()
    #     self.statusbar.setVisible(False)
    #
    # def showNormal(self):
    #     """重写恢复事件"""
    #     super().showNormal()
    #     self.statusbar.setVisible(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # 获取窗口大小信息
        new_size = event.size()
        old_size = event.oldSize()

        # 更新窗口大小标签
        print(f"窗口大小: {new_size.width()} x {new_size.height()} (旧大小: {old_size.width()} x {old_size.height()})")

        if new_size.width() >= self.window_max_width and new_size.height() >= self.window_max_height:
            print("chang to max")
            self.statusbar.setVisible(False)
        else:
            print("chang to normal")
            self.statusbar.setVisible(True)

        if new_size.width() > self.window_max_width:
            self.window_max_width = new_size.width()

        if new_size.height() > self.window_max_height:
            self.window_max_height = new_size.height()

        print(self.windowState())

        if self.windowState()==Qt.WindowNoState:
            print("nomal")
        elif self.windowState()==Qt.WindowMaximized:
            print("max")
        else:
            print("other")



    def connection_handle(self):
        self.BuddyList.topLevelItem(0).setText(0, "等待登录加载中...")
        connection = ConnectionDialog(self)
        connection.configured.connect(self.on_configured)  # 连接对话框如果连接成功将触发当前Application.py文件中的on_configured函数
        connection.connectcancel.connect(self.on_rejected)  # 连接对话框如果连接成功将触发当前Application.py文件中的on_configured函数
        connection.exec_()  # actionConnection是ui_mainwindow的菜单项，该项触发ConnectionDialog对象的运行

    def cjrtest(self):
        print("testingcjr")

    def toggle_search_box(self):
        print("search...")

    def get_all_agent(self):
        agent_cfgs = query_AgentCfg_All()
        for agent_cfg in agent_cfgs:
            agent = Agent(agent_cfg)
            global_agent_list[agent_cfg.user_id] = agent
        # print("global_agent_list.values",)

    def handletogglechatbox(self):

        # self.newWindow = NewWindow()
        # self.newWindow.show()

        self.hide()
        # qtmodern.windows.ModernWindow(window).hide(self)
        self.chatbox.exec_()
        self.show()

    @pyqtSlot()  # 也可以没有这个
    # @pyqtSlot(int)#不能用这个
    def on_configured(self, status=STATUS.available):
        if not self.connectorThread:

            print("on_configured")
            print("status", status)
            self.connectorThread = ConnectorThread(status)
            self.connectorThread.start()
            self.connectorThread.message.connect(self.BuddyList.message)
            self.connectorThread.error.connect(self.error)
            self.connectorThread.connected.connect(self.connected)
            # self.connectorThread.disconnected.connect(self.disconnect)
            # self.connectorThread.presence.connect(self.BuddyList.presence)
            # self.connectorThread.debug.connect(self.debug)
            # self.connectorThread.subscriptionRequest.connect(self.subscriptionRequest)
            self.connectorThread.addBuddySig.connect(self.addBuddy)
        elif self.connectorThread.isConnected():
            self.connectorThread.changeStatus(status, self.statusEdit.text())
            self.statusEdit.clearFocus()

    def on_rejected(self):
        self.BuddyList.topLevelItem(0).setText(0, "尚未登录")

    @pyqtSlot(str, str, str, str)  # 也可以没有这个
    # @pyqtSlot(int)#不能用这个
    def on_configured_ai(self, user_id, jid, password, status):
        if status == "0":
            img_url = 'images/messageoffline.png'
        elif status == "1":
            img_url = 'images/messageonline.png'
        else:
            img_url = 'images/messagehuman.png'

        if user_id in self.connectorThread_list:
            connectorThread = self.connectorThread_list[user_id]

            if connectorThread.isConnected():
                # 已经连接
                if status == "1":
                    self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))
                    return
                elif status == "2":
                    self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))
                    return
                else:
                    connectorThread.disconnect()
                    buddyList = self.buddylist_list[user_id]
                    buddyList.clear()
                    buddyList.re_init()

                    infoList = self.contactlist_list[user_id]
                    infoList.clear()
                    infoList.re_init()

                    self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))
            else:
                # 未连接

                if status == "1":
                    buddyList = self.buddylist_list[user_id]
                    buddyList.topLevelItem(0).setText(0, "等待登录加载中...")

                    infoList = self.contactlist_list[user_id]
                    infoList.topLevelItem(0).setText(0, "等待登录加载中...")

                    connectorThread.start()

                    infoList.load()
                    self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))

                elif status == "2":
                    buddyList = self.buddylist_list[user_id]
                    buddyList.topLevelItem(0).setText(0, "等待登录加载中...")

                    infoList = self.contactlist_list[user_id]
                    infoList.topLevelItem(0).setText(0, "等待登录加载中...")

                    connectorThread.start()

                    infoList.load()

                    self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))

                else:
                    return

            connectorThread.status = status
        else:

            if status == "0":
                return
            print("on_configured_ai")
            print("user_id", user_id)
            buddyList = self.buddylist_list[user_id]
            infoList = self.contactlist_list[user_id]
            buddyList.topLevelItem(0).setText(0, "等待登录加载中...")
            infoList.topLevelItem(0).setText(0, "等待登录加载中...")
            connectorThread = ConnectorThread(status, jid, password)
            connectorThread.start()
            connectorThread.message.connect(buddyList.message)
            connectorThread.friend_subscribe_request.connect(infoList.get_friend_subscribe_request)
            connectorThread.error.connect(self.error)
            connectorThread.connected.connect(lambda: self.connected_ai(user_id))
            connectorThread.addBuddySig.connect(self.addBuddy)
            infoList.load()
            self.connectorThread_list[user_id] = connectorThread
            self.connectorThread = connectorThread
            self.BuddyList = buddyList
            self.InfoList = infoList

            # 处理在线状态
            # self.toolBox_AiChat.setItemText(self.toolBox_AiChat.findChild(QWidget,user_id), "Ai智能体管理")
            print(self.toolBox_AiChat.findChild(QWidget, user_id))
            print(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)))
            self.toolBox_AiChat.setItemIcon(self.toolBox_AiChat.indexOf(self.toolBox_AiChat.findChild(QWidget, user_id)), QIcon(img_url))

    @pyqtSlot(str, str, str)  # 也可以没有这个
    # @pyqtSlot(int)#不能用这个
    def on_configured_human(self, user_id, jid, password):
        status = STATUS.available

        if user_id in self.connectorThread_human_list:
            connectorThread = self.connectorThread_human_list[user_id]
            if connectorThread.isConnected():
                connectorThread.changeStatus(status, self.statusEdit.text())
                self.statusEdit.clearFocus()
        else:
            print("on_configured_human")
            print("user_id", user_id)
            buddyList = self.buddylist_human_list[user_id]
            buddyList.topLevelItem(0).setText(0, "等待登录加载中...")
            connectorThread = ConnectorThread(status, jid, password)
            connectorThread.start()
            connectorThread.message.connect(buddyList.message)
            connectorThread.error.connect(self.error)
            connectorThread.connected.connect(lambda: self.connected_human(user_id))
            connectorThread.addBuddySig.connect(self.addBuddy)
            self.connectorThread_human_list[user_id] = connectorThread

    @pyqtSlot(int)
    def connection(self, status=STATUS.available):
        if not self.connectorThread:
            self.connectorThread = ConnectorThread(status)
            self.connectorThread.start()
            self.connectorThread.message.connect(self.BuddyList.message)
            self.connectorThread.error.connect(self.error)
            self.connectorThread.connected.connect(self.connected)
            self.connectorThread.disconnected.connect(self.disconnect)
            self.connectorThread.presence.connect(self.BuddyList.presence)
            self.connectorThread.debug.connect(self.debug)
            self.connectorThread.subscriptionRequest.connect(self.subscriptionRequest)
            self.connectorThread.addBuddy.connect(self.addBuddy)
        elif self.connectorThread.isConnected():
            self.connectorThread.changeStatus(status, self.statusEdit.text())
            self.statusEdit.clearFocus()

    def openLink(self, url):
        webbrowser.open(url.toString())

    def disconnectbak(self):
        # self.actionConnection.setEnabled(True)
        # self.actionDeconnection.setEnabled(True)
        # self.statusEdit.hide()
        # self.statusBox.setCurrentIndex(STATUS.unavailable.index)
        tmpconnectorThread = ConnectorThread(STATUS.available)
        tmpconnectorThread.start()
        tmpconnectorThread.message.connect(self.BuddyList.message)
        tmpconnectorThread.error.connect(self.error)
        tmpconnectorThread.connected.connect(self.connected)
        tmpconnectorThread = None

        # if self.connectorThread:
        #     self.connectorThread.disconnect()

        # self.connectorThread = None
        # self.BuddyList.clear()
        # QApplication.instance().quit()

    def disconnect(self):
        self.actionConnection.setEnabled(True)
        self.actionDeconnection.setEnabled(False)

        if self.connectorThread:
            self.connectorThread.disconnect()
            self.connectorThread = None
        # self.BuddyList.clear()
        # QApplication.instance().quit()

    def connected(self):
        print("connected........")
        self.actionConnection.setEnabled(False)
        self.actionDeconnection.setEnabled(True)
        # if self.statusBox.currentIndex() == STATUS.unavailable.index:
        #     self.statusBox.setCurrentIndex(STATUS.available.index)
        # else:
        #     self.connectorThread.changeStatus(self.statusBox.currentIndex(), self.statusEdit.text())
        self.statusEdit.show()
        self.statusEdit.setFocus()

        # while i <100000:
        #     i=i+1
        # self.BuddyList.topLevelItem(0).setText(0,"加载中...")
        self.BuddyList.setConnection(self.connectorThread)
        self.getRoster()
        # self.setAway()
        # self.setOffline()

    def connected_ai(self, user_id):
        connectorThread = self.connectorThread_list[user_id]
        buddyList = self.buddylist_list[user_id]
        buddyList.setConnection(connectorThread)
        infoList = self.contactlist_list[user_id]
        infoList.setConnection(connectorThread)
        self.getRoster_ai(connectorThread, user_id)

    def connected_human(self, user_id):
        connectorThread = self.connectorThread_human_list[user_id]
        buddyList = self.buddylist_human_list[user_id]
        buddyList.setConnection(connectorThread)
        infoList = self.contactlist_list[user_id]
        infoList.setConnection(connectorThread)
        self.getRoster_human(connectorThread, user_id)

    def error(self, title, content):
        QMessageBox.critical(self, title, content, QMessageBox.Ok)

    def closeEvent(self, event):
        self.quit()

    def quit(self):
        self.disconnect()
        QApplication.instance().quit()

    @pyqtSlot(int)
    def changeStatus(self, index=-1):
        if index == -1:
            index = self.statusBox.currentIndex()
        if index == STATUS.unavailable:
            self.statusEdit.hide()
            self.disconnect()
        else:
            self.connection(index)

    def getRoster(self):
        # pass
        roster = self.connectorThread.getRoster()
        for buddy in roster:
            self.BuddyList.addItem(buddy)
        self.BuddyList.itemDoubleClicked.connect(self.sendMessage)
        global_buddy_list["buddylist"] = self.BuddyList
        print("connect buddylist")

    def getRoster_ai(self, connectorThread, user_id):
        # pass
        roster = connectorThread.getRoster()
        buddyList = self.buddylist_list[user_id]
        for buddy in roster:
            buddyList.addItem(buddy)
        buddyList.itemDoubleClicked.connect(self.sendMessage)
        global_buddy_list["buddylist"] = buddyList
        print("connect buddylist")

    def getRoster_human(self, connectorThread, user_id):
        # pass
        roster = connectorThread.getRoster()
        buddyList = self.buddylist_human_list[user_id]
        for buddy in roster:
            buddyList.addItem(buddy)
        buddyList.itemDoubleClicked.connect(self.sendMessage)
        global_buddy_list["buddylist"] = buddyList
        print("connect buddylist")

    @pyqtSlot(QTreeWidgetItem, int)
    def sendMessage(self, item, column):
        print("in clickitem")
        # id_value = item.data(column, Qt.UserRole)
        # # print("双击了：", id_value)
        # if id_value == None:
        #     return (False)
        if item.__class__.__name__ == "BuddyGroup":
            return

        if item and item.type() == QTreeWidgetItem.UserType + 1:
            item.sendMessage()

    @pyqtSlot(bool)
    def setAway(self, checked=-1):
        if checked == -1:
            checked = self.actionAway_buddies.isChecked()
        self.BuddyList.setAway(not checked)

    @pyqtSlot(bool)
    def setOffline(self, checked=-1):
        if checked == -1:
            checked = self.actionOffline_buddies.isChecked()
        self.BuddyList.setOffline(not checked)

    @pyqtSlot(bool)
    def showagenthome(self, checked=-1):

        file_path = os.path.join(Path(__file__).resolve().parent, "scripts", "index3.html")
        print(file_path)
        url_string = QUrl.fromLocalFile(file_path)

        # agent_home.page().load(QUrl("http://www.ai-sns.org/index_agent.html"))
        # self.agent_home.page().load(QUrl(url_string))

        # channel = QWebChannel()
        # shared = Myshared()
        # channel.registerObject("con", shared)
        #
        # self.agent_home.page().setWebChannel(channel)

        # if checked == -1:
        #     checked = self.actionShow_agent_homepage.isChecked()
        # print(checked)
        # if checked:
        #    self.conversation_pages.setCurrentWidget(self.agent_home_frame)
        # else:
        #     self.conversation_pages.setCurrentIndex(1)

    @pyqtSlot(bool)
    def showaihome(self, checked=-1):
        if checked == -1:
            checked = self.actionShow_ai_homepage.isChecked()
        print(checked)
        if checked:
            self.conversation_pages.setCurrentWidget(self.ai_home_frame)
        else:
            self.conversation_pages.setCurrentIndex(1)

    @pyqtSlot(bool)
    def showhumanhome(self, checked=-1):
        if checked == -1:
            checked = self.actionShow_human_homepage.isChecked()
        print(checked)
        if checked:
            self.conversation_pages.setCurrentWidget(self.human_home_frame)
        else:
            self.conversation_pages.setCurrentIndex(1)

    @pyqtSlot(bool)
    def showkmhome(self, checked=-1):
        if checked == -1:
            checked = self.actionShow_km_homepage.isChecked()
        print(checked)
        if checked:
            self.conversation_pages.setCurrentWidget(self.km_home_frame)
        else:
            self.conversation_pages.setCurrentIndex(1)

    @pyqtSlot(bool)
    def showpluginhome(self, checked=-1):
        if checked == -1:
            checked = self.actionShow_plugin_homepage.isChecked()
        print(checked)
        if checked:
            self.conversation_pages.setCurrentWidget(self.plugin_home_frame)
        else:
            self.conversation_pages.setCurrentIndex(1)

    @pyqtSlot(dict)
    def subscriptionRequest(self, presence):
        request = RosterRequest(self, self.connectorThread.jabber, presence)
        request.show()

    @pyqtSlot(str)
    def debug(self, message):
        self.te.append(datetime.datetime.now().strftime("[%H:%M:%S]") + " : \n" + message)

    def swapConsole(self):
        self.console.setWindowTitle("XML Console")
        self.console.resize(QSize(1024, 500))
        self.console.show()
        self.console.raise_()

    def opendochelp(self):
        # self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
        self.conversation_pages.setCurrentIndex(1)

    def openwebhelp(self):
        webbrowser.open("http://www.ai-sns.org")

    @pyqtSlot()
    def addBuddy(self, item=None):
        print("in addbuddy")
        if self.connectorThread:
            if item:
                jid = item.jid
            else:
                jid = ""
            newBuddy = AddBuddyDialog(self, self.connectorThread.jabber_xmpp, list(self.BuddyList.groups.keys()), jid)
            newBuddy.show()

    def addGroup(self):
        newGroup = AddGroupDialog(self, self.BuddyList)
        newGroup.show()


def __description() -> str:
    return "Create your own anime meta data"


def __usage() -> str:
    return "vrv-meta.py --service vrv"


def __init_cli() -> argparse:
    parser = argparse.ArgumentParser(description=__description(), usage=__usage())
    parser.add_argument(
        '-l', '--log', default='DEBUG', help="""
        Specify log level which should use. Default will always be DEBUG, choose between the following options
        CRITICAL, ERROR, WARNING, INFO, DEBUG
        """
    )
    parser.add_argument(
        '-d', '--directory', default=f'{FileSystem.get_plugins_directory()}', help="""
        (Optional) Supply a directory where plugins should be loaded from. The default is ./plugins
        """
    )
    return parser


def __print_program_end() -> None:
    print("-----------------------------------")
    print("End of execution")
    print("-----------------------------------")


def __init_app(parameters: dict) -> None:
    return PluginEngine(options=parameters).start()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = QApplication(sys.argv)

    __cli_args = __init_cli().parse_args()
    print("cjrok")
    print(__cli_args.log)
    print("cjrok2")

    # load plugins load插件
    # initiate plugins 初始化插件
    __init_app({
        'log_level': __cli_args.log,
        'directory': __cli_args.directory
    })

    print(global_plugin_list)

    window = MainWindow()
    window.setWindowIcon(QIcon("C:\\dev\\ai-sns\\PyTalk\\pytalk\\images\\aisns.png"))

    # window.showMaximized()
    #
    # apply_stylesheet(app, theme='dark_blue.xml')#qt_material
    #
    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5')) #qdarkstyle
    # app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5', palette=LightPalette())) #qdarkstyle
    window.showagenthome()

    # channel = QWebChannel()
    # shared = Myshared()
    # channel2 = QWebChannel()
    # shared2 = Myshared()
    # setup_web_channel(channel2,shared2)
    # window.show()
    # showchannel(window)
    # # channel = QWebChannel()
    # # shared = Myshared()
    # # channel.registerObject("con", shared)
    # #
    # # window.agent_home.page().setWebChannel(channel)
    #
    #
    # channel = QWebChannel()
    # shared = Myshared()
    # channel.registerObject("con", shared)
    #
    # window.agent_home.page().setWebChannel(channel)
    #
    #
    #
    #
    #
    qtmodern.styles.light(app)  # qtmodern dark or light
    mw = qtmodern.windows.ModernWindow(window)  # qtmodern

    #

    if sys.platform == "win32":
        mw.showMaximized()  # qtmodern 保留操作系统工具栏
    elif sys.platform == "darwin":
        mw.showFullScreen()  # 不保留操作系统工具栏
    else:
        mw.showMaximized()  # qtmodern 保留操作系统工具栏
    #
    mw.setWindowIcon(QIcon("C:\\dev\\ai-sns\\PyTalk\\pytalk\\images\\aisns.png"))
    app.setWindowIcon(QIcon("C:\\dev\\ai-sns\\PyTalk\\pytalk\\images\\aisns.png"))

    __eb = ExplanationBalloon(window.toolBox_Workflow, 300.0, 200.0, 'This is explanation balloon made out of PyQt')
    __eb.setFont(QFont('Arial', 14))
    __eb.setBackgroundColor(QColor(50, 50, 50, 255))
    __eb.show()

    # window.showMaximized()
    sys.exit(app.exec_())
