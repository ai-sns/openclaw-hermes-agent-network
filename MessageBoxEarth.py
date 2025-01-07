import os
import math
import pyautogui
from PyQt5 import QtGui
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QWidget, QDialog, QScrollArea, QGridLayout, QPushButton, QVBoxLayout, QFileDialog
from PyQt5.QtCore import QSettings, Qt, QUrl, pyqtSignal, QThread
from PyQt5.QtGui import QIcon
from ui.ui_MessageWidgetEarth import Ui_MessageWidget
import hashlib
import webbrowser
import emoji
from pytalk.speaker import Speaker_Log
# 主要用于发送附件
import asyncio
from typing import Optional
import time

from globals import global_agent_list
import time
import sys
import logging
from pathlib import Path
from getpass import getpass
from argparse import ArgumentParser

import slixmpp
from slixmpp import JID
from slixmpp.exceptions import IqTimeout
import json
log = logging.getLogger(__name__)
from Agent import Agent, AgentMode
from db.DBFactory import query_AgentCfg, add_AIChatMessages,add_AgentTask
from pluginsmanager.plugins_gui.tab_plugin import load_plugin
from util import generate_random_id, add_msg_to_message_window,get_myai_send_msg_title_formatted,add_msg_to_message_windowv3, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, toggle_msg_loading_status, add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, add_attachment_to_message_window, image_to_base64, generate_img_tag,add_msg_to_message_window_with_markdown_and_highlightv2

class WorkerThread(QThread):
    finished = pyqtSignal(str, str)


    def __init__(self, agent,  question, messages, web_browser, task_id,parent=None):
        super(WorkerThread, self).__init__(parent)
        global current_agent
        self.agent = agent
        current_agent = self.agent
        agent_cfg = agent.agent_cfg
        self.agentcfg = agent_cfg
        self.task_id = task_id
        self.agent_name = agent_cfg.name
        self.question = question
        self.messages = messages
        self.web_browser = web_browser
        self.browser_page = web_browser.page()

    def run(self):
        agent = self.agent
        browser_page = self.browser_page
        agent.set_mode(AgentMode.ChatOnly)
        question = self.question
        answer = agent.ask_it(question, self.messages, browser_page, self.task_id)

        self.finished.emit(question, answer)

    def stop(self):
        print("thread stopping....")
        del self.agent
        print("del agent....")


class HttpUpload(slixmpp.ClientXMPP):

    """
    A basic client asking an entity if they confirm the access to an HTTP URL.
    """

    def __init__(
        self,
        jid: JID,
        password: str,
        recipient: JID,
        filename: Path,
        domain: Optional[JID] = None,
        encrypted: bool = False,
        url:str="",
    ):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.recipient = recipient
        self.filename = filename
        self.domain = domain
        self.encrypted = encrypted

        self.add_event_handler("session_start", self.start)

    async def start(self, event):
        log.info('Uploading file %s...', self.filename)

        file_name = Path(self.filename).name
        try:
            upload_file = self['xep_0363'].upload_file
            if self.encrypted and not self['xep_0454']:
                print(
                    'The xep_0454 module isn\'t available. '
                    'Ensure you have \'cryptography\' '
                    'from extras_require installed.',
                    file=sys.stderr,
                )
                return
            elif self.encrypted:
                upload_file = self['xep_0454'].upload_file
            self.url = await upload_file(
                self.filename, domain=self.domain, timeout=10,
            )
        except IqTimeout:
            raise TimeoutError('Could not send message in time')
        log.info('Upload success!')

        log.info('Sending file to %s', self.recipient)
        html = (
            f'<body xmlns="http://www.w3.org/1999/xhtml">'
            f'<a href="{self.url}">{file_name}</a></body>'
        )
        print("html",html)
        message = self.make_message(mto=self.recipient, mbody=self.url, mhtml=html)
        message['oob']['url'] = self.url
        message.send()
        self.disconnect()


class EmojiDialog(QDialog):
    def __init__(self, parent=None):
        super(EmojiDialog, self).__init__(parent)
        self.setWindowTitle('选择表情包')

        current_mouse_position = pyautogui.position()
        x_position, y_position = current_mouse_position
        # 打印鼠标位置的 x 和 y 坐标
        print("当前鼠标位置 - X坐标：", x_position)
        print("当前鼠标位置 - Y坐标：", y_position)

        self.setGeometry(x_position-300, y_position-320, 600, 300)



        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget(scroll_area)
        self.scroll_content.setGeometry(0, 0, 600, 300)

        grid_layout = QGridLayout(self.scroll_content)
        self.emoji_buttons = []

        emojis = emoji.EMOJI_DATA.values()
        row, col = 0, 0

        for e in emojis:
            emoji_button = QPushButton(emoji.emojize(e['en']), self)
            emoji_button.clicked.connect(self.selectEmoji)
            grid_layout.addWidget(emoji_button, row, col)
            col += 1
            if col > 4:
                col = 0
                row += 1

        scroll_area.setWidget(self.scroll_content)

        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def selectEmoji(self):
        button = self.sender()
        selected_emoji = button.text()
        self.accepted_emoji = selected_emoji
        self.accept()


class MessageBox(QWidget, Ui_MessageWidget):
    signal_msg_received = pyqtSignal()
    def __init__(self, parent, con, jid, name,ai_chat_cfg):
        super(MessageBox, self).__init__(parent)
        self.human_take_over=False
        self.jid = jid
        self.name = name
        self.con = con
        self.ai_chat_cfg = ai_chat_cfg
        self.conversation_id = ""
        self.messages=[]
        self.page_index = 0
        self.map_mode = 'org'
        self.setupUi(self)

        # self.messageBrowser.setPlainText("")
        # self.messageBrowser.setOpenLinks(False)

        self.messageEdit.setFocus()

        self.fontButton.clicked.connect(self.showEmoji)
        self.sendButton.clicked.connect(self.sendMessage_click)
        self.videoButton.clicked.connect(self.sendfile)
        self.enterButton.clicked.connect(self.enterscene)
        self.exitButton.clicked.connect(self.exitscene)
        self.humantakeoverCheckBox.clicked.connect(self.humantakeoverhandle)

        # self.messageBrowser.anchorClicked.connect(self.openLink)
        # agent=global_agent_list["002"]#Musk
        snsaccount=self.ai_chat_cfg.account
        agent_cfg = query_AgentCfg(snsaccount=snsaccount)
        self.agent = Agent(agent_cfg)
        self.kmselectedList=[]
        self.pluginselectedList = []
        self.current_received_msg=""
        self.signal_msg_received.connect(self.ask_agent_and_reply_message)

        self.humantakeoverCheckBox.setChecked(self.human_take_over)
        self.messages = []

        self.is_browser_page_loaded = False
        self.event_cache=None
        self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理
        self.first_event=None
        self.first_reply = ""
        self.ChatCompletions_flag = ""
        self.ChatCompletions_content = ""

        #plugin相关
        self.chess_role=None
        self.chinese_chess_role = None
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."

    def setConnection(self,connection):
        self.con = connection

    def increment_page_index(self):
        self.page_index += 1
        return self.page_index
    def new_chat(self):
        # self.human_take_over = False
        #
        # self.conversation_id = ""
        # self.messages = []
        #
        #
        # self.messageEdit.setFocus()
        #
        #
        #
        # self.is_browser_page_loaded = False
        # self.event_cache = None
        # self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理
        # self.first_event = None
        # self.first_reply = ""
        # self.ChatCompletions_flag = ""
        # self.ChatCompletions_content = ""
        #
        # # plugin相关
        # self.chess_role = None
        # self.chinese_chess_role = None
        # self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."

        #***********todo:附件的界面也要清除掉****************


        self.messageBrowser.page().runJavaScript('re_init()')




    def onLoadFinished(self):
        self.is_browser_page_loaded = True
        self.receiveMessage(self.event_cache)
        # time.sleep(1)
        # self.append_message("cjrokcjrokcjrok")
        # # self.messageEdit.setFocus()

    def receiveMessage(self, event):

        if self.ChatCompletions_flag=="1":
            self.ChatCompletions_content = event['body']


        if event is not None:
            if "//中国象棋bak" in event['body']:
                tabs = self.tabWidget
                load_plugin(tabs, "中国象棋", "chinese_chess", "ChineseChess", content="red")
                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())
            elif "//中国象棋" in event['body']:

                tabs = self.tabWidget
                move_str = event['body'].replace("//中国象棋", "")
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")

                if chess_view is None:
                    self.chinese_chess_role = "black"#如果收到消息尚未初始化，说明是对手启动棋局，我方为黑方
                    self.tab_plugin = load_plugin(tabs, "中国象棋", "chinese_chess", "ChineseChess", content="red")
                    self.tab_plugin.handle_received_message(self, move_str)
                    return_msg=""
                else:
                    return_msg = self.tab_plugin.handle_received_message(self, move_str)


                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())


            elif "//国际象棋" in event['body']:

                tabs = self.tabWidget
                move_str = event['body'].replace("//国际象棋", "")
                chess_view = tabs.findChild(QWebEngineView, "chess")

                if chess_view is None:
                    self.chess_role = "black"#如果收到消息尚未初始化，说明是对手启动棋局，我方为黑方
                    self.tab_plugin = load_plugin(tabs, "国际象棋", "chess", "Chess", content=move_str)
                    self.tab_plugin.handle_received_message(self, move_str)
                    return_msg=""
                else:
                    return_msg = self.tab_plugin.handle_received_message(self, move_str)


                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())


        if self.is_browser_page_loaded==False:
            self.event_cache = event
            return
        else:
            self.event_cache = None

        if not event is None:
            message = f"""\n<strong><span style="color: darkblue; font-size:14px;">{self.name} :</span></strong> {event['body']}"""
            self.append_message(message)

            if self.map_mode != 'org':
                browser_page = self.messageBrowser.page()
                browser_page.runJavaScript(f"send_talk_message('{str(event['from']).split('/')[0]}','wangwang@xabber.de','{event['body']}')")
            else:
                self.message_handler.send_talk_message(str(event['from']).split('/')[0], "wangwang@xabber.de", event['body'])

            #以下是AI自动对话相关

            if "//国际象棋" in event['body']:
                if return_msg=="":
                    return
                else:
                    self.current_received_msg = return_msg
            elif "//中国象棋" in event['body']:

                return

                if return_msg=="":
                    return
                else:
                    self.current_received_msg = return_msg

            else:
                self.current_received_msg = event['body']


            if self.human_take_over==False:

                self.signal_msg_received.emit()

    def sendMessage_click(self):

        if self.messageEdit.toPlainText():
            self.sendMessage(self.messageEdit.toPlainText(),True)
            self.messageEdit.clear()
            self.messageEdit.setAcceptRichText(False)
            self.messageEdit.setTextColor(QtGui.QColor(0, 0, 0))
            self.messageEdit.setPlainText("")
            self.messageEdit.setStyleSheet("""
                        QTextEdit {
                            border-radius: 2px; /* 设置圆角 */
                            border: 1px solid #c0c0c0; /* 设置边框 */
                            background: transparent; 
                            color: black;
                        }
                        QTextEdit:focus {
                            border-color: #61addf; /* 设置焦点时的边框颜色 */
                        }
                    """)
            # self.messageEdit.setAcceptRichText(True)


    #ChatCompletions
    def sendMessage(self,content,by_click=False):
        if content:
            if "//中国象棋" in content:
                tabs = self.tabWidget
                move_str = content.replace("//中国象棋", "")
                chess_view = tabs.findChild(QWebEngineView, "chinese_chess")
                if chess_view is None:
                    self.chinese_chess_role = "red"  # 如果发送消息尚未初始化，说明是我方启动棋局，我方为红方
                    self.tab_plugin = load_plugin(tabs, "中国象棋", "chinese_chess", "ChineseChess", content="red")
                    self.tab_plugin.handle_send_message(self, move_str)
                else:
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage(return_msg,True)
                    return

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

            elif "//国际象棋" in content:
                tabs = self.tabWidget
                move_str = content.replace("//国际象棋", "")
                chess_view = tabs.findChild(QWebEngineView, "chess")
                if chess_view is None:
                    self.chess_role = "white"  # 如果发送消息尚未初始化，说明是我方启动棋局，我方为白方
                    self.tab_plugin = load_plugin(tabs, "国际象棋", "chess", "Chess", content=move_str)
                    self.tab_plugin.handle_send_message(self, move_str)
                else:
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    # return_msg="//国际象棋"+return_msg
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage(return_msg)
                    return

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())


            message = f"""<strong><span style="color: darkblue; font-size:14pt;">用户 :</span></strong><br> {content}<br>"""
            browser_page = self.messageBrowser.page()
            if by_click:
                browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')
                add_AIChatMessages(self.conversation_id, 0, "", content, self.ai_chat_cfg.name, self.ai_chat_cfg.account, self.name, self.jid, False)
            self.append_message(message)

            if self.chess_role and "//国际象棋" not in content:
                self.con.send_message(self.jid, "//国际象棋" + content)
            elif self.chinese_chess_role and "//中国象棋" not in content:
                self.con.send_message(self.jid, "//中国象棋" + content)
            else:
                self.con.send_message(self.jid, content)
            if self.map_mode != 'org':
                browser_page.runJavaScript(f"send_talk_message('wangwang@xabber.de','chenchen@xabber.de','{content}')")
            else:
                self.message_handler.send_talk_message("wangwang@xabber.de", "chenchen@xabber.de", content)

    def handle_get_msg_from_js(self,msg):
        self.sendMessage(msg)

    def ChatCompletions(self,content):
        reply=""
        if content:
           self.con.send_message(self.jid, content)
           self.ChatCompletions_flag="1"

        while self.ChatCompletions_flag=="1":
            time.sleep(1)
            if self.ChatCompletions_content!="":
                reply=self.ChatCompletions_content
                self.ChatCompletions_content=""
                self.ChatCompletions_flag = ""
                break
        return reply






    def append_message(self,message):
        browser_page = self.messageBrowser.page()
        self.message_handler.pass_message(message)#先去掉
        # browser_page.runJavaScript("window.scrollTo(0, document.body.scrollHeight);")



    def ask_agent_and_reply_message(self):
        pluginname = "OpenAI"
        modelname = "OpenAI"

        # vector_path = "C:\\dev\\ai-sns\\PyTalk\\pytalk\\vector_store"
        # embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
        vector_path = ""
        embedding_model_name = ''


        question = self.current_received_msg

        agent = self.agent
        # agent.give_it_plugin(pluginname)#使用配置里面的第一个
        agent.give_it_km(vector_path, embedding_model_name)
        self.messages.append({"role": "user", "content": question})

        if self.messages[0]["role"] != "system":
            self.messages.insert(0, {"role": "system", "content": f"{self.system_role_prompt}"})

        messages = self.messages

        speaker = Speaker_Log()
        agent.give_it_speaker(speaker)

        if self.chess_role:
            messages=[messages[0],messages[-1]]

        self.thread = WorkerThread(agent,question, messages, self.messageBrowser, self.conversation_id)
        self.thread.finished.connect(self.on_agent_replied)
        self.thread.start()


    def on_agent_replied(self,question,content):

        self.first_reply=content
        if self.chess_role:
            tmp_content=content.strip()
            tmp_content=tmp_content.replace(".","")

            self.sendMessage("//国际象棋"+tmp_content[-4:])
        elif self.chinese_chess_role:
            tmp_content=content.strip()
            tmp_content=tmp_content.replace(".","")

            self.sendMessage("//中国象棋"+tmp_content[-4:])

        else:
            self.sendMessage(content,True)

    def showTaskResult(self, agent_name, task_result):
        message = f"""\n<strong><span style="color: darkblue; font-size:14px;">{agent_name} :</span></strong> {task_result}"""
        self.append_message(message)


    def startVideo(self):
        hash_value = hashlib.md5(self.jid.encode('utf-8')).hexdigest()
        url = f"http://jtalk.trunat.fr/jtalk/?{hash_value}"
        message = f"""\n<a href="{url}">Click here to join the videoChat</a>"""
        self.append_message(message)
        self.con.send_message(self.jid, f"Join me for a video chat here: {url}")
        webbrowser.open(url)

    def sendfile(self):
        filepath=self.setOpenFileName()
        if filepath == "":
            return("")
        filename = Path(filepath).name
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Setup the command line arguments.
        parser = ArgumentParser()
        parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                            action="store_const",
                            dest="loglevel",
                            const=logging.ERROR,
                            default=logging.INFO)
        parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                            action="store_const",
                            dest="loglevel",
                            const=logging.DEBUG,
                            default=logging.INFO)

        # JID and password options.
        parser.add_argument("-j", "--jid", dest="jid", default="wangwang@xabber.de",
                            help="JID to use")
        parser.add_argument("-p", "--password", dest="password", default="wangwang",
                            help="password to use")

        # Other options.
        parser.add_argument("-r", "--recipient", dest="recipient", required=False, default="yangyang@xabber.de",
                            help="Recipient JID")
        parser.add_argument("-f", "--file", dest="file", required=False, default=filepath,
                            help="File to send")
        parser.add_argument("--domain",
                            help="Domain to use for HTTP File Upload (leave out for your own server’s)")

        parser.add_argument("-e", "--encrypt", dest="encrypted",
                            help="Whether to encrypt", action="store_true",
                            default=False)

        args = parser.parse_args()

        # Setup logging.
        logging.basicConfig(level=args.loglevel,
                            format='%(levelname)-8s %(message)s')

        if args.jid is None:
            args.jid = JID(input("Username: "))
        if args.password is None:
            args.password = getpass("Password: ")

        domain = args.domain
        if domain is not None:
            domain = JID(domain)

        if args.encrypted:
            print(
                'You are using the --encrypt flag. '
                'Be aware that the transport being used is NOT end-to-end '
                'encrypted. The server will be able to decrypt the file.',
                file=sys.stderr,
            )

        xmpp = HttpUpload(
            jid=args.jid,
            password=args.password,
            recipient=JID(args.recipient),
            filename=Path(args.file),
            domain=domain,
            encrypted=args.encrypted,
        )
        xmpp.register_plugin('xep_0066')
        xmpp.register_plugin('xep_0071')
        xmpp.register_plugin('xep_0128')
        xmpp.register_plugin('xep_0363')
        try:
            xmpp.register_plugin('xep_0454')
        except slixmpp.plugins.base.PluginNotFound:
            log.error(
                'Could not load xep_0454. '
                'Ensure you have \'cryptography\' from extras_require installed.'
            )

        # Connect to the XMPP server and start processing XMPP stanzas.
        xmpp.connect()
        xmpp.process(forever=False)



        message = f"""\n<strong><em><span style="color: darkred; font-size:14px;">{self.tr("Me")} :</span></em></strong> <a href='{xmpp.url}'>{filename}</a>"""
        self.append_message(message)


    def load_urlbak(self,url_str,is_local=False):

        if is_local:
            file_path = os.path.join(os.getcwd(), "scripts", url_str)
            url = QUrl.fromLocalFile(file_path)
        else:
            url = QUrl(url_str)
        self.messageBrowser.page().load(url)

    def load_url(self, url_str, is_local=False):
        # 获取当前时间戳
        timestamp = int(time.time())

        if is_local:
            file_path = os.path.join(os.getcwd(), "scripts", url_str)
            url = QUrl.fromLocalFile(file_path)
        else:
            # 为 URL 添加时间戳
            if '?' in url_str:
                url_str += f"&timestamp={timestamp}"
            else:
                url_str += f"?timestamp={timestamp}"

            url = QUrl(url_str)

        self.messageBrowser.page().load(url)


    def enterscene(self,type,address):
        self.map_mode = 'app'
        if type == "plugin":
            os.system(address)
        else:
            self.load_url(address)

    def exitscene(self):
        self.map_mode = 'org'
        self.load_url("map.html",True)

    def handle_user_send_im(self,from_user,to_user,msg):
        self.con.send_message(to_user,msg)




    def humantakeoverhandle(self):
        self.human_take_over=self.humantakeoverCheckBox.isChecked()

    def toggle_output_checkbox(self, state):
        if state == Qt.Checked:
            self.splitter.setSizes([300, 1])
        else:
            self.splitter.setSizes([1, ])

    def setOpenFileName(self):
        openFileNameLabel=""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                "QFileDialog.getOpenFileName()", openFileNameLabel,
                "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            openFileNameLabel=fileName
        print(openFileNameLabel)
        return openFileNameLabel

    def setOpenFileNames(self):
        openFilesPath = ""
        openFileNameLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                "QFileDialog.getOpenFileNames()", openFilesPath,
                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            openFilesPath = files[0]
            openFileNamesLabel=("[%s]" % ', '.join(files))
        print(openFileNamesLabel)
        return openFileNamesLabel

    def showEmoji(self):
        dialog = EmojiDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_emoji = dialog.accepted_emoji
            print(selected_emoji)
            self.messageEdit.insertPlainText(selected_emoji)
            self.messageEdit.setFocus()

    def openLink(self, url):
        webbrowser.open(url.toString())
