import os
import threading

import openai
import shutil
import urllib
from datetime import datetime
import requests
import os
from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QDialog, QTreeWidgetItemIterator, QPlainTextEdit
from PyQt5.QtCore import QSettings, Qt, QUrl, QFile, QFileInfo
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem

from langchainhandler import getvectorkm_String
from speaker import Speaker
from ui.ui_TaskPageWidget import Ui_TaskPageWidget
import hashlib
import webbrowser
from db.DBFactory import add_AgentTask
import http.client
import json
from pluginsmanager import PluginEngine, PluginType

import argparse

from pluginsmanager import FileSystem

import urllib.request
import re

import sys

sys.path.append("..")
sys.path.append("../..")
from kmselect import FreezeTableDialog as KmFreezeTableDialog
from pluginselect import FreezeTableDialog as PluginFreezeTableDialog, ComboBoxDelegate, ButtonDelegate
from pluginselect_tool import FreezeTableDialog as PluginFreezeTableDialogTool, ComboBoxDelegate as ComboBoxDelegateTool, ButtonDelegate as ButtonDelegateTool

from db.DBFactory import add_KMCfg, query_KMCfg_All, update_KMCfg, delete_KMCfg, query_KMCfg
from db.DBFactory import add_PluginMng, query_PluginMng_All, update_PluginMng, delete_PluginMng, query_PluginMng,query_PluginMng_All_Tool
from db.DBFactory import update_AgentCfg
from globals import global_plugin_list
from globals import global_buddy_list
import globals
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from RPAStocksHandle import StocksHandle
from Agent import Agent, AgentMode
import pyautogui
import pyperclip
import os
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QWidget, QMenu, QAction, QHBoxLayout, QShortcut
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QKeySequence
from pluginsmanager.plugins_gui.tab_plugin import load_plugin
from pluginsmanager.plugins_headless.plugin_mng import load_plugin as load_plugin_tool
pyautogui.PAUSE = 0.5
from pathlib import Path
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, toggle_msg_loading_status, add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, add_attachment_to_message_window,image_to_base64,generate_img_tag

current_agent = None



class WorkerThread(QThread):
    finished = pyqtSignal(str, str, int)

    def __init__(self, agent, task_id, is_first, question, messages, pluginname, vector_path, embedding_model_name, modelname, web_browser, speaker, attachment_content_list, plugin_tool_record_selected_list,parent=None):
        super(WorkerThread, self).__init__(parent)
        global current_agent
        self.agent = agent
        current_agent = self.agent
        agent_cfg = agent.agent_cfg
        self.agentcfg = agent_cfg
        self.task_id = task_id
        self.is_first = is_first
        self.agent_name = agent_cfg.name
        self.question = question
        self.messages = messages
        self.pluginname = pluginname
        self.vector_path = vector_path
        self.embedding_model_name = embedding_model_name
        self.modelname = modelname
        self.web_browser = web_browser
        self.browser_page = web_browser.page()
        self.speaker = speaker
        self.attachment_content_list=attachment_content_list
        self.plugin_tool_record_selected_list = plugin_tool_record_selected_list

    def run(self):
        agent = self.agent
        browser_page = self.browser_page
        agent.set_mode(AgentMode.ChatOnly)
        agent.give_it_plugin(self.pluginname)
        agent.give_it_plugin_tool(self.plugin_tool_record_selected_list)
        agent.give_it_attachment_content_list(self.attachment_content_list)
        agent.give_it_km(self.vector_path, self.embedding_model_name)
        agent.give_it_speaker(self.speaker)
        question = self.question
        answer = agent.ask_it(question, self.messages, browser_page,self.task_id)
        attachment_content_list=json.dumps(agent.attachment_content_list, ensure_ascii=False)#km部分已经在agent中进行了处理，添加进去了
        # attachment_doc_content=json.dumps(agent.attachment_doc_content)
        # attachment_image_list=json.dumps(agent.attachment_image_list)
        if agent.chat_mode=="task":
            # question="用户发出了上述指令"
            question = "exit"
        record_id = add_AgentTask(self.task_id, question, question, answer, self.modelname, self.agentcfg.user_id, self.is_first,attachment_content_list)

        agent.remove_all_attachment()
        self.finished.emit(question, answer, record_id)

    def stop(self):
        print("thread stopping....")
        del self.agent
        print("del agent....")

class WorkerThreadGP(QThread):


    def __init__(self):
        super(WorkerThreadGP, self).__init__(None)
        print("ok")


    def run(self):
        stocks_handle = StocksHandle()
        companies = ['google', 'amazon', 'meta', 'apple']
        stocks_handle.get_Stocks(companies)
        print("准备发文件...")
        os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
        time.sleep(1)
        self.click_image_position("search.png")
        name = '文件传输助手'
        pyperclip.copy(name)
        # 模拟按下和释放Ctr1键和V键
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)  # 避免操作过快
        self.click_image_position("sendfile.png")
        directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
        NOW = datetime.now()
        PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
        file_path = PPTX
        pyperclip.copy(file_path)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.press('enter')




class TaskPage(QWidget, Ui_TaskPageWidget):
    def __init__(self, application, agent):
        super(TaskPage, self).__init__()
        self.agent = agent
        agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg
        self.name = agent_cfg.name
        self.application = application
        self.task_id = ""
        self.is_first = True
        self.task_type = 'single'
        self.page_index = 0
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."
        # 后面可能会有system提示，这句在这个地方，可能会导致像百川这样不允许多个system的role的提示语，会报错，百度不允许有system这个角色
        self.messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        # self.messages = []
        self.task_command=""

        self.messages_attachment_list = {}
        self.messages_km_list = {}
        self.messages_attachment_content = {}
        self.messages_km_content = {}


        # 指定历史(指定上下文相关)
        self.selected_history_messages = []
        self.selected_history_index = []

        # 附件信息相关
        self.current_attachment_list = []
        # self.current_attachment_content="___________以下是相关附件信息,供你参考___________"
        # self.current_attachment_content = ""  # 合并后的附件内容
        self.attachment_content_list = []  # 附件内容列表
        self.attachment_labels = []  # 存储所有附件标签

        self.conten_menu_closing=False#是否正在关闭内容菜单，用于给全选按钮做判断条件

        self.setupUi(self)

        # webengineview去掉了
        # self.messageBrowser.setPlainText("")
        # self.messageBrowser.setOpenLinks(False)

        self.messageEdit.setFocus()

        self.sendButton.clicked.connect(self.sendMessage)
        self.stopButton.clicked.connect(self.stopMessage)
        self.llm_button.clicked.connect(self.opendialog_plugin_tool)
        self.newButton.clicked.connect(self.new_task_by_btn)
        self.attach_button.clicked.connect(self.add_attachment)
        self.kmButton.clicked.connect(self.opendialogkm)
        self.model_select_checkbox.stateChanged.connect(self.toggle_model_select_type)
        self.task_mode_checkbox.stateChanged.connect(self.toggle_chat_mode)
        self.history_mode_checkbox.stateChanged.connect(self.toggle_history_mode)
        self.prompt_combobox.currentIndexChanged.connect(self.set_prompt_string)
        # self.manage_button.clicked.connect(self.on_manage_button_clicked)#由下面这句替代了
        self.manage_button.mousePressEvent=self.manage_button_mousePressEvent



        self.update_prompts_in_combobox()

        self.shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.shortcut.activated.connect(self.toggle_search_box)

        self.tab_plugin=None

        self.kmselectedList = []
        if agent_cfg.kms != "":
            self.kmselectedList = agent_cfg.kms.split(",")
        print(self.kmselectedList)
        self.pluginselectedList = []
        self.pluginselectedList_tool = []
        self.plugin_tool_record_selected_list = []
        if agent_cfg.plugins != "":
            self.pluginselectedList = agent_cfg.plugins.split(",")
        print(self.pluginselectedList)
        self.set_messagebox_placeholder()

        # self.messageBrowser.anchorClicked.connect(self.openLink)
        print(self.application.cjr)
        self.is_browser_page_loaded = False
        self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

    def onLoadFinished(self):
        self.is_browser_page_loaded = True
        self.messageEdit.setFocus()

    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key_Delete:
    #         print("deleting......")

    def keyPressEvent(self, event):
        # if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
        if event.key() == Qt.Key_F1 and event.modifiers() == Qt.ControlModifier:
            print("Ctrl+F detected")
            self.toggle_search_box()

    def increment_page_index(self):
        self.page_index += 1
        return self.page_index

    def set_selected_history_index(self, i, status):
        print("set_selected_history_index i:", i)
        print("set_selected_history_index status", status)
        if status == "checked":
            self.add_selected_history_index(i)
        else:
            self.remove_selected_history_index(i)
        self.get_selected_history_messages()



    def toggle_content_menu(self,status="checked"):
        if status == "checked":
            self.content_menu_group_box.setVisible(True)

            for i in range(self.hboxlayout.count()):
                item = self.hboxlayout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(False)  # 隐藏每个控件

            for i in range(self.hboxlayout1.count()):
                item = self.hboxlayout1.itemAt(i)
                if item.widget():
                    item.widget().setVisible(False)  # 隐藏每个控件

        else:#由关闭按钮触发
            self.conten_menu_closing = True
            self.content_menu_group_box.setVisible(False)

            for i in range(self.hboxlayout.count()):
                item = self.hboxlayout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)  # 隐藏每个控件

            for i in range(self.hboxlayout1.count()):
                item = self.hboxlayout1.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)  # 隐藏每个控件
            self.stopButton.setVisible(False)

            if self.history_mode_checkbox.isChecked()==False:

                self.task_mode_checkboxa.setChecked(False)
                # self.toggle_page_all_checkboxes_status(0)
                self.messageBrowser.page().runJavaScript("hideCheckboxes()")



    def edit_selected_content(self, code_type, text,file_name=""):
        tabs = self.tabWidget
        if code_type.lower() == "mermaid" or (code_type.lower() == "markdown" and "```mermaid" in text) :
            text=text.replace("```mermaid","")
            print("mermaid")
            editor = tabs.findChild(QPlainTextEdit, "mermaid_editor")
            if editor is None:
                load_plugin(tabs, "Mermaid", "mermaid_editor", "MermaidEditor", content=text)
                editor = tabs.findChild(QPlainTextEdit, "mermaid_editor")
                editor.parent().file_name = file_name
            else:
                editor.setPlainText(text)
                editor.parent().file_name = file_name

            for index in range(tabs.count()):
                if tabs.tabText(index) == "Mermaid":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        elif code_type.lower() == "mindmap" or (code_type.lower() == "markdown" and (("思维导图" in text and "##" in text) or ("mindmap" in text and "##" in text)  or (text.startswith("#") and "##" in text)) ):

            print("mindmap")
            editor = tabs.findChild(QPlainTextEdit, "mindmap_editor")
            if editor is None:
                load_plugin(tabs, "MindMap", "mindmap_editor", "MindMapEditor", content=text)
                editor = tabs.findChild(QPlainTextEdit, "mindmap_editor")
                editor.parent().file_name = file_name
            else:
                editor.setPlainText(text)
                editor.parent().file_name = file_name

            for index in range(tabs.count()):
                if tabs.tabText(index) == "MindMap":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        else:

            editor=tabs.findChild(QPlainTextEdit,"code_editor")
            if editor is None:
                load_plugin(tabs,"编辑器","code_editor","CodeEditor",content=text)
                editor=tabs.findChild(QPlainTextEdit,"code_editor")
                editor.parent().file_name = file_name
            else:
                editor.setPlainText(text)
                editor.parent().file_name=file_name

            for index in range(tabs.count()):
                if tabs.tabText(index) == "编辑器":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        if not self.output_checkbox.isChecked():
            self.output_checkbox.setChecked(True)
            self.toggle_output_checkbox(self.output_checkbox.checkState())




    def add_selected_history_index(self, i):
        # Check if 'i' is already in 'self.selected_history_index'
        if i not in self.selected_history_index:
            # Insert 'i' into 'self.selected_history_index' in sorted order
            self.selected_history_index.append(i)
            self.selected_history_index.sort()

    def get_selected_history_messages(self):
        # Clear the selected_history_messages list first
        self.selected_history_messages.clear()
        self.selected_history_messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        # Get the messages corresponding to the indices in selected_history_index
        for index in self.selected_history_index:
            if 0 <= index < len(self.messages):
                self.selected_history_messages.append(self.messages[index])

    def remove_selected_history_index(self, i):
        # Remove the first occurrence of 'i' from 'self.selected_history_index', if it exists
        if i in self.selected_history_index:
            self.selected_history_index.remove(i)

    def new_task(self):
        self.task_id = ""
        self.is_first = True
        # 后面可能会有system提示，这句在这个地方，可能会导致像百川这样不允许多个system的role的提示语，会报错，百度不允许有system这个角色
        # self.messages = [{"role": "system", "content": "You are a helpful assistant who provides concise and accurate information."}]
        self.messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        self.task_command = ""
        # self.messages = []
        self.page_index = 0
        self.selected_history_messages = []
        self.selected_history_index = []

        self.messages_attachment_list = {}
        self.messages_km_list = {}
        self.messages_attachment_content = {}
        self.messages_km_content = {}

        # 指定历史(指定上下文相关)
        self.selected_history_messages = []
        self.selected_history_index = []

        # 附件信息相关
        self.current_attachment_list = []
        # self.current_attachment_content="___________以下是相关附件信息,供你参考___________"
        # self.current_attachment_content = ""  # 合并后的附件内容
        self.attachment_content_list = []  # 附件内容列表
        self.attachment_labels = []  # 存储所有附件标签

        #***********todo:附件的界面也要清除掉****************


        self.messageBrowser.page().runJavaScript('re_init()')

    def receiveMessage(self, event):
        message = f"""\n<strong><span style="color: darkblue">{self.name} :</span></strong> {event.getBody()}"""
        self.messageBrowser.append(message)

    def __description(self) -> str:
        return "Create your own anime meta data"

    def __usage(self) -> str:
        return "vrv-meta.py --service vrv"

    def __init_cli(self) -> argparse:
        parser = argparse.ArgumentParser(description=self.__description(), usage=self.__usage())
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

    def __print_program_end(self) -> None:
        print("-----------------------------------")
        print("End of execution")
        print("-----------------------------------")

    def __init_app(self, parameters: dict) -> None:
        return PluginEngine(options=parameters).start()

    def click_image_position(self, img):
        # time.sleep(1)
        image_1 = pyautogui.locateOnScreen(img, grayscale=True, confidence=0.7)
        # time.sleep(1)
        center = pyautogui.center(image_1)
        pyautogui.click(center)

    def sendMessage(self):

        if self.messageEdit.toPlainText():

            __cli_args = self.__init_cli().parse_args()
            print(__cli_args.log)


            if len(self.pluginselectedList) > 0:
                # self.pluginselectedList: [(1, '2', 'ChatGLM连接器: 1.0.0', 'chatglm_connector')]#row index,record id,plugin name,plugin alias
                # pluginname=self.pluginselectedList[0][2]
                # modelname=self.pluginselectedList[0][3]
                pluginname = self.pluginselectedList[0]
                llm = global_plugin_list[pluginname]
                config = llm.get_config()
                modelname = config.get("model", "")
                modelname = pluginname + f"({modelname})"

                # 增加以下语句，如果有选中的插件，则认为是指定了，而不是自动，暂时不要使用checkbox进行指定
                self.agent.model_select_type = 'specify'

            else:
                pluginname = "ChatGLM连接器: 1.0.0"  # 设置缺省连接器
                modelname = "ChatGLM"  # 指定缺省模型
                # 增加以下语句，如果没选中插件，则认为是自动，暂时不要使用checkbox进行指定
                self.agent.model_select_type = 'auto'

            if self.agent.model_select_type == 'auto':
                if "天气" in self.messageEdit.toPlainText():
                    pluginname = "百度文心连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "ERNIE-3.5-8K"
                    modelname = pluginname + f"({modelname})"
                elif "编写" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"
                elif "写一个" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"

                elif "算法" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"

                elif "介绍一下" in self.messageEdit.toPlainText():
                    pluginname = "讯飞星火连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "general"
                    modelname = pluginname + f"({modelname})"

            promptstr = ""
            print("the km list", self.kmselectedList)
            print("the km list length", len(self.kmselectedList))
            if len(self.kmselectedList) > 0:
                print("self.kmselectedList:")
                print(self.kmselectedList)
                km_name = self.kmselectedList[0]
                km_record = query_KMCfg(name=km_name)
                vector_path = km_record.kmpath
                print("vector_path:", vector_path)
                # vector_path = "vector_store/vector"  # 先写死
                vector_path = os.path.join(os.getcwd(), "km",vector_path,"vector")
                print("vector_path2:", vector_path)
                embedding_model_name = km_record.embeddingmodel
            else:
                vector_path = ""
                embedding_model_name = ""

            plugin_tool_record_selected_list = self.plugin_tool_record_selected_list



            question = self.messageEdit.toPlainText()
            self.task_command = question


            speaker = self.speaker


            if self.messageEdit.toPlainText() == "ymcymc":

                print(os.getcwd())
                print(os.path.join(os.getcwd(), "scripts", "index.html"))
                print(urllib.request.pathname2url(os.path.join(os.getcwd(), "index.html")))
                url_string = urllib.request.pathname2url(os.path.join(os.getcwd(), "scripts", "index.html"))
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("okcjrok")
            elif self.messageEdit.toPlainText() == "szrszr":

                url_string = "https://bridge.yfd.net:1443/"
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("szrszr")
            elif self.messageEdit.toPlainText() == "zdfzdf":

                self.application.conversation_pages.setCurrentIndex(1)  # 首页
                self.application.ShowAiChatStack()

                if "buddylist" in global_buddy_list:
                    buddylist = global_buddy_list["buddylist"]
                    buddylist.send_message("yangyang@xabber.de", "您好，我自动发")
            elif "to autogen:" in self.messageEdit.toPlainText():
                global current_agent

                current_agent.human_reply = self.messageEdit.toPlainText()[11:]
                message = f"""{current_agent.human_reply}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')
            elif "*给我画*" in self.messageEdit.toPlainText():
                #废弃掉不通过这个判断走了，现在是在Agent中走
                urls=self.generate_image(self.messageEdit.toPlainText())
                print("给我画url:",urls)



                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br><br>"')
                modelname="Dall-e-3"
                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '"')

                # 创建新的附件元素

                img_element=''.join(f"<img src='{url}'>&nbsp;&nbsp;&nbsp;&nbsp;<br>" for url in urls)
                print(img_element)
                # 添加附件元素到页面中
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += `' + img_element + '`')
            elif "股票" in self.messageEdit.toPlainText():
                print("股票")

                os.system("C:\\dev\\rpa\\Stocks_RPA_Python\\venv\\Scripts\\python.exe C:/dev/rpa/Stocks_RPA_Python/mainv2.py")

                # stocks_handle = StocksHandle()
                # companies = ['google', 'amazon', 'meta', 'apple']
                # stocks_handle.get_Stocks(companies)

                # self.thread = WorkerThreadGP()
                #
                # self.thread.start()

                # print("准备发文件...")
                # os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
                # time.sleep(1)
                # self.click_image_position("search.png")
                # name = '文件传输助手'
                # pyperclip.copy(name)
                # # 模拟按下和释放Ctr1键和V键
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)  # 避免操作过快
                # self.click_image_position("sendfile.png")
                # directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
                # NOW = datetime.now()
                # PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
                # file_path = PPTX
                # pyperclip.copy(file_path)
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)
                # pyautogui.press('enter')

                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

                message = f"""处理完毕！"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')


            elif "//中国象棋" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                load_plugin(tabs, "中国象棋", "chinese_chess", "ChineseChess", content="red")
                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

            elif "//国际象棋" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                move_str=self.messageEdit.toPlainText().replace("//国际象棋","")
                chess_view = tabs.findChild(QWebEngineView, "chess")
                if chess_view is None:
                    self.tab_plugin=load_plugin(tabs, "国际象棋", "chess", "Chess", content=move_str)

                    # 设置定时器，5秒后调用 my_function
                    # timer = threading.Timer(1, self.tab_plugin.handle_send_message(self, move_str))
                    #
                    # # 启动定时器
                    # timer.start()
                    return_msg=self.tab_plugin.handle_send_message(self, move_str)
                    # self.messageEdit.setPlainText(return_msg)
                    # self.sendMessage()
                else:
                    # chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{svg}`")
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage()

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

                # return False

            elif "//数字人" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                move_str=self.messageEdit.toPlainText().replace("//数字人","")
                digital_human_view = tabs.findChild(QWebEngineView, "digital_human")
                if digital_human_view is None:
                    self.tab_plugin=load_plugin(tabs, "数字人", "digital_human", "DigitalHuman", content=move_str)

                    # 设置定时器，5秒后调用 my_function
                    # timer = threading.Timer(1, self.tab_plugin.handle_send_message(self, move_str))
                    #
                    # # 启动定时器
                    # timer.start()
                    return_msg=self.tab_plugin.handle_send_message(self, move_str)
                    # self.messageEdit.setPlainText(return_msg)
                    # self.sendMessage()
                else:
                    # chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{svg}`")
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage()

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

                # return False


            elif self.speaker.status == "wait_for_feedback":
                 self.speaker.human_feedback=self.messageEdit.toPlainText()

                 page_index = self.increment_page_index()
                 message = get_user_ask_msg_title_formatted(page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)

                 message = get_user_ask_msg_content_formatted(question)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 2)
                 self.messageBrowser.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

                 page_index = self.increment_page_index()
                 message = get_agent_reply_msg_title_formatted(modelname, page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)


            else:
                task_id = self.task_id
                if task_id == "":
                    task_id = generate_random_id()
                    self.task_id = task_id
                    self.is_first = True

                if len(self.current_attachment_list)>0:
                    directory_path = os.path.join('resource', 'attachment', 'chat', task_id)
                    os.makedirs(directory_path, exist_ok=True)

                for file_path in self.current_attachment_list:
                    try:
                        shutil.copy(file_path, directory_path)
                    except Exception as e:
                        print(f"Error copying file {file_path}: {e}")

                page_index = self.increment_page_index()
                if self.history_mode_checkbox.isChecked()==True:
                    message = get_user_ask_msg_title_formatted(page_index,show_checkbox="inline-block",checked="checked")
                    self.set_selected_history_index(page_index,"checked")
                else:
                    message = get_user_ask_msg_title_formatted(page_index)
                add_msg_to_message_window(self.messageBrowser.page(), message, 1)

                message = get_user_ask_msg_content_formatted(question)
                add_msg_to_message_window(self.messageBrowser.page(), message, 2)
                self.messageBrowser.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")


                #处理附件
                if len(self.current_attachment_list) > 0:
                    add_attachment_to_message_window(self.messageBrowser.page(),directory_path, self.current_attachment_list, 2)

                if self.messages[0]["role"] != "system":
                    self.messages.insert(0, {"role": "system", "content": f"{self.system_role_prompt}"})
                elif self.messages[0]["role"] == "system":
                    self.messages[0]["content"] = self.system_role_prompt

                if "百度" in modelname:
                    if self.messages[0]["role"] == "system":
                        self.messages = self.messages[1:]

                self.messages.append({"role": "user", "content": self.messageEdit.toPlainText()})

                page_index = self.increment_page_index()

                if self.history_mode_checkbox.isChecked()==True:

                    message = get_agent_reply_msg_title_formatted(modelname, page_index,show_checkbox="inline-block",checked="checked")

                else:
                    message = get_agent_reply_msg_title_formatted(modelname, page_index)


                add_msg_to_message_window(self.messageBrowser.page(), message, 1)


                #挪到顶部了
                # message_handler = self.message_handler
                # web_browser = self.messageBrowser
                # speaker = Speaker(message_handler, web_browser)
                # self.speaker =speaker

                if self.agent.history_mode == 'specify':
                    messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]+self.selected_history_messages
                    messages.append({"role": "user", "content": self.messageEdit.toPlainText()})
                else:
                    messages = self.messages[:]

                attachment_content_list=self.attachment_content_list

                self.thread = WorkerThread(self.agent, task_id, self.is_first,question, messages, pluginname, vector_path, embedding_model_name, modelname, self.messageBrowser, speaker,attachment_content_list,plugin_tool_record_selected_list)
                self.thread.finished.connect(self.onTaskFinished)
                self.thread.start()

                # ***************????????????

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
            # if self.agent.chat_mode == 'chat':
            #     self.stopButton.setVisible(True)
            #     self.sendButton.setVisible(False)
            self.modelname=modelname
            self.messageEdit.setFocus()

    def stopMessage(self):
        self.thread.stop()

        del self.thread
        print("after deling2")
        self.speaker.stop_speaker=True
        self.stopButton.setVisible(False)
        self.sendButton.setVisible(True)


    #             self.messageEdit.setHtml("""
    #             <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 390 390" width="200" height="200"><desc><pre>r n b q k b n r
    # p p p . . p p p
    # . . . . . . . .
    # . . . p p . . .
    # . . . P P . . .
    # . . . . . . . .
    # P P P . . P P P
    # R N B Q K B N R</pre></desc><defs><g id="white-pawn" class="white pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linecap="round" /></g><g id="white-knight" class="white knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#ffffff; stroke:#000000;" /><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#ffffff; stroke:#000000;" /><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#000000; stroke:#000000;" /><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#000000; stroke:#000000;" /></g><g id="white-bishop" class="white bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#fff" stroke-linecap="butt"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zM15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" /></g><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke-linejoin="miter" /></g><g id="white-rook" class="white rook" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12 36v-4h21v4H12zM11 14V9h4v2h5V9h5v2h5V9h4v5" stroke-linecap="butt" /><path d="M34 14l-3 3H14l-3-3" /><path d="M31 17v12.5H14V17" stroke-linecap="butt" stroke-linejoin="miter" /><path d="M31 29.5l1.5 2.5h-20l1.5-2.5" /><path d="M11 14h23" fill="none" stroke-linejoin="miter" /></g><g id="white-queen" class="white queen" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM24.5 7.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM41 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM16 8.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM33 9a2 2 0 1 1-4 0 2 2 0 1 1 4 0z" /><path d="M9 26c8.5-1.5 21-1.5 27 0l2-12-7 11V11l-5.5 13.5-3-15-3 15-5.5-14V25L7 14l2 12zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt" /><path d="M11.5 30c3.5-1 18.5-1 22 0M12 33.5c6-1 15-1 21 0" fill="none" /></g><g id="white-king" class="white king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6M20 8h5" stroke-linejoin="miter" /><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#fff" stroke-linecap="butt" stroke-linejoin="miter" /><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#fff" /><path d="M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" /></g><g id="black-pawn" class="black pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#000" stroke="#000" stroke-width="1.5" stroke-linecap="round" /></g><g id="black-knight" class="black knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#000000; stroke:#000000;" /><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#000000; stroke:#000000;" /><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#ececec; stroke:#ececec;" /><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#ececec; stroke:#ececec;" /><path d="M 24.55,10.4 L 24.1,11.85 L 24.6,12 C 27.75,13 30.25,14.49 32.5,18.75 C 34.75,23.01 35.75,29.06 35.25,39 L 35.2,39.5 L 37.45,39.5 L 37.5,39 C 38,28.94 36.62,22.15 34.25,17.66 C 31.88,13.17 28.46,11.02 25.06,10.5 L 24.55,10.4 z " style="fill:#ececec; stroke:none;" /></g><g id="black-bishop" class="black bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zm6-4c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#000" stroke-linecap="butt" /><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke="#fff" stroke-linejoin="miter" /></g><g id="black-rook" class="black rook" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12.5 32l1.5-2.5h17l1.5 2.5h-20zM12 36v-4h21v4H12z" stroke-linecap="butt" /><path d="M14 29.5v-13h17v13H14z" stroke-linecap="butt" stroke-linejoin="miter" /><path d="M14 16.5L11 14h23l-3 2.5H14zM11 14V9h4v2h5V9h5v2h5V9h4v5H11z" stroke-linecap="butt" /><path d="M12 35.5h21M13 31.5h19M14 29.5h17M14 16.5h17M11 14h23" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="miter" /></g><g id="black-queen" class="black queen" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#000" stroke="none"><circle cx="6" cy="12" r="2.75" /><circle cx="14" cy="9" r="2.75" /><circle cx="22.5" cy="8" r="2.75" /><circle cx="31" cy="9" r="2.75" /><circle cx="39" cy="12" r="2.75" /></g><path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt" /><path d="M11 38.5a35 35 1 0 0 23 0" fill="none" stroke-linecap="butt" /><path d="M11 29a35 35 1 0 1 23 0M12.5 31.5h20M11.5 34.5a35 35 1 0 0 22 0M10.5 37.5a35 35 1 0 0 24 0" fill="none" stroke="#fff" /></g><g id="black-king" class="black king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6" stroke-linejoin="miter" /><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#000" stroke-linecap="butt" stroke-linejoin="miter" /><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#000" /><path d="M20 8h5" stroke-linejoin="miter" /><path d="M32 29.5s8.5-4 6.03-9.65C34.15 14 25 18 22.5 24.5l.01 2.1-.01-2.1C20 18 9.906 14 6.997 19.85c-2.497 5.65 4.853 9 4.853 9M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" stroke="#fff" /></g></defs><rect x="7.5" y="7.5" width="375" height="375" fill="none" stroke="#212121" stroke-width="15" /><g transform="translate(20, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M23.328 10.016q-1.742 0-2.414.398-.672.398-.672 1.36 0 .765.5 1.218.508.445 1.375.445 1.196 0 1.914-.843.727-.852.727-2.258v-.32zm2.867-.594v4.992h-1.437v-1.328q-.492.797-1.227 1.18-.734.375-1.797.375-1.343 0-2.14-.75-.79-.758-.79-2.024 0-1.476.985-2.226.992-.75 2.953-.75h2.016V8.75q0-.992-.656-1.531-.649-.547-1.829-.547-.75 0-1.46.18-.711.18-1.368.539V6.062q.79-.304 1.532-.453.742-.156 1.445-.156 1.898 0 2.836.984.937.985.937 2.985z" /></g><g transform="translate(20, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M23.328 10.016q-1.742 0-2.414.398-.672.398-.672 1.36 0 .765.5 1.218.508.445 1.375.445 1.196 0 1.914-.843.727-.852.727-2.258v-.32zm2.867-.594v4.992h-1.437v-1.328q-.492.797-1.227 1.18-.734.375-1.797.375-1.343 0-2.14-.75-.79-.758-.79-2.024 0-1.476.985-2.226.992-.75 2.953-.75h2.016V8.75q0-.992-.656-1.531-.649-.547-1.829-.547-.75 0-1.46.18-.711.18-1.368.539V6.062q.79-.304 1.532-.453.742-.156 1.445-.156 1.898 0 2.836.984.937.985.937 2.985z" /></g><g transform="translate(65, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.922 10.047q0-1.586-.656-2.485-.649-.906-1.79-.906-1.14 0-1.796.906-.649.899-.649 2.485 0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.789-.898.656-.906.656-2.492zm-4.89-3.055q.452-.781 1.14-1.156.695-.383 1.656-.383 1.594 0 2.586 1.266 1 1.265 1 3.328 0 2.062-1 3.328-.992 1.266-2.586 1.266-.96 0-1.656-.375-.688-.383-1.14-1.164v1.312h-1.446V2.258h1.445z" /></g><g transform="translate(65, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.922 10.047q0-1.586-.656-2.485-.649-.906-1.79-.906-1.14 0-1.796.906-.649.899-.649 2.485 0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.789-.898.656-.906.656-2.492zm-4.89-3.055q.452-.781 1.14-1.156.695-.383 1.656-.383 1.594 0 2.586 1.266 1 1.265 1 3.328 0 2.062-1 3.328-.992 1.266-2.586 1.266-.96 0-1.656-.375-.688-.383-1.14-1.164v1.312h-1.446V2.258h1.445z" /></g><g transform="translate(110, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M25.96 6v1.344q-.608-.336-1.226-.5-.609-.172-1.234-.172-1.398 0-2.172.89-.773.883-.773 2.485 0 1.601.773 2.492.774.883 2.172.883.625 0 1.234-.164.618-.172 1.227-.508v1.328q-.602.281-1.25.422-.64.14-1.367.14-1.977 0-3.14-1.242-1.165-1.242-1.165-3.351 0-2.14 1.172-3.367 1.18-1.227 3.227-1.227.664 0 1.296.14.633.134 1.227.407z" /></g><g transform="translate(110, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M25.96 6v1.344q-.608-.336-1.226-.5-.609-.172-1.234-.172-1.398 0-2.172.89-.773.883-.773 2.485 0 1.601.773 2.492.774.883 2.172.883.625 0 1.234-.164.618-.172 1.227-.508v1.328q-.602.281-1.25.422-.64.14-1.367.14-1.977 0-3.14-1.242-1.165-1.242-1.165-3.351 0-2.14 1.172-3.367 1.18-1.227 3.227-1.227.664 0 1.296.14.633.134 1.227.407z" /></g><g transform="translate(155, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.973 6.992V2.258h1.437v12.156h-1.437v-1.312q-.453.78-1.149 1.164-.687.375-1.656.375-1.586 0-2.586-1.266-.992-1.266-.992-3.328 0-2.063.992-3.328 1-1.266 2.586-1.266.969 0 1.656.383.696.375 1.149 1.156zm-4.899 3.055q0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.796-.898.657-.906.657-2.492 0-1.586-.657-2.485-.656-.906-1.796-.906-1.141 0-1.797.906-.649.899-.649 2.485z" /></g><g transform="translate(155, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.973 6.992V2.258h1.437v12.156h-1.437v-1.312q-.453.78-1.149 1.164-.687.375-1.656.375-1.586 0-2.586-1.266-.992-1.266-.992-3.328 0-2.063.992-3.328 1-1.266 2.586-1.266.969 0 1.656.383.696.375 1.149 1.156zm-4.899 3.055q0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.796-.898.657-.906.657-2.492 0-1.586-.657-2.485-.656-.906-1.796-.906-1.141 0-1.797.906-.649.899-.649 2.485z" /></g><g transform="translate(200, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M26.555 9.68v.703h-6.61q.094 1.484.89 2.265.806.774 2.235.774.828 0 1.602-.203.781-.203 1.547-.61v1.36q-.774.328-1.586.5-.813.172-1.649.172-2.093 0-3.32-1.22-1.219-1.218-1.219-3.296 0-2.148 1.157-3.406 1.164-1.266 3.132-1.266 1.766 0 2.79 1.14 1.03 1.134 1.03 3.087zm-1.438-.422q-.015-1.18-.664-1.883-.64-.703-1.703-.703-1.203 0-1.93.68-.718.68-.828 1.914z" /></g><g transform="translate(200, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M26.555 9.68v.703h-6.61q.094 1.484.89 2.265.806.774 2.235.774.828 0 1.602-.203.781-.203 1.547-.61v1.36q-.774.328-1.586.5-.813.172-1.649.172-2.093 0-3.32-1.22-1.219-1.218-1.219-3.296 0-2.148 1.157-3.406 1.164-1.266 3.132-1.266 1.766 0 2.79 1.14 1.03 1.134 1.03 3.087zm-1.438-.422q-.015-1.18-.664-1.883-.64-.703-1.703-.703-1.203 0-1.93.68-.718.68-.828 1.914z" /></g><g transform="translate(245, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M25.285 2.258v1.195H23.91q-.773 0-1.078.313-.297.312-.297 1.125v.773h2.367v1.117h-2.367v7.633H21.09V6.781h-1.375V5.664h1.375v-.61q0-1.46.68-2.124.68-.672 2.156-.672z" /></g><g transform="translate(245, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M25.285 2.258v1.195H23.91q-.773 0-1.078.313-.297.312-.297 1.125v.773h2.367v1.117h-2.367v7.633H21.09V6.781h-1.375V5.664h1.375v-.61q0-1.46.68-2.124.68-.672 2.156-.672z" /></g><g transform="translate(290, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.973 9.937q0-1.562-.649-2.421-.64-.86-1.804-.86-1.157 0-1.805.86-.64.859-.64 2.421 0 1.555.64 2.415.648.859 1.805.859 1.164 0 1.804-.86.649-.859.649-2.414zm1.437 3.391q0 2.234-.992 3.32-.992 1.094-3.04 1.094-.757 0-1.429-.117-.672-.11-1.304-.344v-1.398q.632.344 1.25.508.617.164 1.257.164 1.414 0 2.118-.743.703-.734.703-2.226v-.711q-.446.773-1.141 1.156-.695.383-1.664.383-1.61 0-2.594-1.227-.984-1.226-.984-3.25 0-2.03.984-3.257.985-1.227 2.594-1.227.969 0 1.664.383t1.14 1.156V5.664h1.438z" /></g><g transform="translate(290, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M24.973 9.937q0-1.562-.649-2.421-.64-.86-1.804-.86-1.157 0-1.805.86-.64.859-.64 2.421 0 1.555.64 2.415.648.859 1.805.859 1.164 0 1.804-.86.649-.859.649-2.414zm1.437 3.391q0 2.234-.992 3.32-.992 1.094-3.04 1.094-.757 0-1.429-.117-.672-.11-1.304-.344v-1.398q.632.344 1.25.508.617.164 1.257.164 1.414 0 2.118-.743.703-.734.703-2.226v-.711q-.446.773-1.141 1.156-.695.383-1.664.383-1.61 0-2.594-1.227-.984-1.226-.984-3.25 0-2.03.984-3.257.985-1.227 2.594-1.227.969 0 1.664.383t1.14 1.156V5.664h1.438z" /></g><g transform="translate(335, 1) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M26.164 9.133v5.281h-1.437V9.18q0-1.243-.485-1.86-.484-.617-1.453-.617-1.164 0-1.836.742-.672.742-.672 2.024v4.945h-1.445V2.258h1.445v4.765q.516-.789 1.211-1.18.703-.39 1.617-.39 1.508 0 2.282.938.773.93.773 2.742z" /></g><g transform="translate(335, 375) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M26.164 9.133v5.281h-1.437V9.18q0-1.243-.485-1.86-.484-.617-1.453-.617-1.164 0-1.836.742-.672.742-.672 2.024v4.945h-1.445V2.258h1.445v4.765q.516-.789 1.211-1.18.703-.39 1.617-.39 1.508 0 2.282.938.773.93.773 2.742z" /></g><g transform="translate(0, 335) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.754 26.996h2.578v-8.898l-2.805.562v-1.437l2.79-.563h1.578v10.336h2.578v1.328h-6.72z" /></g><g transform="translate(375, 335) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.754 26.996h2.578v-8.898l-2.805.562v-1.437l2.79-.563h1.578v10.336h2.578v1.328h-6.72z" /></g><g transform="translate(0, 290) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M8.195 26.996h5.508v1.328H6.297v-1.328q.898-.93 2.445-2.492 1.555-1.57 1.953-2.024.758-.851 1.055-1.437.305-.594.305-1.164 0-.93-.657-1.516-.648-.586-1.695-.586-.742 0-1.57.258-.82.258-1.758.781v-1.593q.953-.383 1.781-.578.828-.196 1.516-.196 1.812 0 2.89.906 1.079.907 1.079 2.422 0 .72-.274 1.368-.265.64-.976 1.515-.196.227-1.243 1.313-1.046 1.078-2.953 3.023z" /></g><g transform="translate(375, 290) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M8.195 26.996h5.508v1.328H6.297v-1.328q.898-.93 2.445-2.492 1.555-1.57 1.953-2.024.758-.851 1.055-1.437.305-.594.305-1.164 0-.93-.657-1.516-.648-.586-1.695-.586-.742 0-1.57.258-.82.258-1.758.781v-1.593q.953-.383 1.781-.578.828-.196 1.516-.196 1.812 0 2.89.906 1.079.907 1.079 2.422 0 .72-.274 1.368-.265.64-.976 1.515-.196.227-1.243 1.313-1.046 1.078-2.953 3.023z" /></g><g transform="translate(0, 245) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M11.434 22.035q1.132.242 1.765 1.008.64.766.64 1.89 0 1.727-1.187 2.672-1.187.946-3.375.946-.734 0-1.515-.149-.774-.14-1.602-.43V26.45q.656.383 1.438.578.78.196 1.632.196 1.485 0 2.258-.586.782-.586.782-1.703 0-1.032-.727-1.61-.719-.586-2.008-.586h-1.36v-1.297h1.423q1.164 0 1.78-.46.618-.47.618-1.344 0-.899-.64-1.375-.633-.485-1.82-.485-.65 0-1.391.141-.743.14-1.633.437V16.95q.898-.25 1.68-.375.788-.125 1.484-.125 1.797 0 2.844.82 1.046.813 1.046 2.204 0 .968-.554 1.64-.555.664-1.578.922z" /></g><g transform="translate(375, 245) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M11.434 22.035q1.132.242 1.765 1.008.64.766.64 1.89 0 1.727-1.187 2.672-1.187.946-3.375.946-.734 0-1.515-.149-.774-.14-1.602-.43V26.45q.656.383 1.438.578.78.196 1.632.196 1.485 0 2.258-.586.782-.586.782-1.703 0-1.032-.727-1.61-.719-.586-2.008-.586h-1.36v-1.297h1.423q1.164 0 1.78-.46.618-.47.618-1.344 0-.899-.64-1.375-.633-.485-1.82-.485-.65 0-1.391.141-.743.14-1.633.437V16.95q.898-.25 1.68-.375.788-.125 1.484-.125 1.797 0 2.844.82 1.046.813 1.046 2.204 0 .968-.554 1.64-.555.664-1.578.922z" /></g><g transform="translate(0, 200) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M11.016 18.035L7.03 24.262h3.985zm-.414-1.375h1.984v7.602h1.664v1.312h-1.664v2.75h-1.57v-2.75H5.75v-1.523z" /></g><g transform="translate(375, 200) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M11.016 18.035L7.03 24.262h3.985zm-.414-1.375h1.984v7.602h1.664v1.312h-1.664v2.75h-1.57v-2.75H5.75v-1.523z" /></g><g transform="translate(0, 155) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.719 16.66h6.195v1.328h-4.75v2.86q.344-.118.688-.172.343-.063.687-.063 1.953 0 3.094 1.07 1.14 1.07 1.14 2.899 0 1.883-1.171 2.93-1.172 1.039-3.305 1.039-.735 0-1.5-.125-.758-.125-1.57-.375v-1.586q.703.383 1.453.57.75.188 1.586.188 1.351 0 2.14-.711.79-.711.79-1.93 0-1.219-.79-1.93-.789-.71-2.14-.71-.633 0-1.266.14-.625.14-1.281.438z" /></g><g transform="translate(375, 155) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.719 16.66h6.195v1.328h-4.75v2.86q.344-.118.688-.172.343-.063.687-.063 1.953 0 3.094 1.07 1.14 1.07 1.14 2.899 0 1.883-1.171 2.93-1.172 1.039-3.305 1.039-.735 0-1.5-.125-.758-.125-1.57-.375v-1.586q.703.383 1.453.57.75.188 1.586.188 1.351 0 2.14-.711.79-.711.79-1.93 0-1.219-.79-1.93-.789-.71-2.14-.71-.633 0-1.266.14-.625.14-1.281.438z" /></g><g transform="translate(0, 110) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M10.137 21.863q-1.063 0-1.688.727-.617.726-.617 1.992 0 1.258.617 1.992.625.727 1.688.727 1.062 0 1.68-.727.624-.734.624-1.992 0-1.266-.625-1.992-.617-.727-1.68-.727zm3.133-4.945v1.437q-.594-.28-1.204-.43-.601-.148-1.195-.148-1.562 0-2.39 1.055-.82 1.055-.938 3.188.46-.68 1.156-1.04.696-.367 1.531-.367 1.758 0 2.774 1.07 1.023 1.063 1.023 2.899 0 1.797-1.062 2.883-1.063 1.086-2.828 1.086-2.024 0-3.094-1.547-1.07-1.555-1.07-4.5 0-2.766 1.312-4.406 1.313-1.649 3.524-1.649.593 0 1.195.117.61.118 1.266.352z" /></g><g transform="translate(375, 110) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M10.137 21.863q-1.063 0-1.688.727-.617.726-.617 1.992 0 1.258.617 1.992.625.727 1.688.727 1.062 0 1.68-.727.624-.734.624-1.992 0-1.266-.625-1.992-.617-.727-1.68-.727zm3.133-4.945v1.437q-.594-.28-1.204-.43-.601-.148-1.195-.148-1.562 0-2.39 1.055-.82 1.055-.938 3.188.46-.68 1.156-1.04.696-.367 1.531-.367 1.758 0 2.774 1.07 1.023 1.063 1.023 2.899 0 1.797-1.062 2.883-1.063 1.086-2.828 1.086-2.024 0-3.094-1.547-1.07-1.555-1.07-4.5 0-2.766 1.312-4.406 1.313-1.649 3.524-1.649.593 0 1.195.117.61.118 1.266.352z" /></g><g transform="translate(0, 65) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.25 16.66h7.5v.672L9.516 28.324H7.867l3.985-10.336H6.25z" /></g><g transform="translate(375, 65) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M6.25 16.66h7.5v.672L9.516 28.324H7.867l3.985-10.336H6.25z" /></g><g transform="translate(0, 20) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M10 22.785q-1.125 0-1.773.602-.641.601-.641 1.656t.64 1.656q.649.602 1.774.602t1.773-.602q.649-.61.649-1.656 0-1.055-.649-1.656-.64-.602-1.773-.602zm-1.578-.672q-1.016-.25-1.586-.945-.563-.695-.563-1.695 0-1.399.993-2.211 1-.813 2.734-.813 1.742 0 2.734.813.993.812.993 2.21 0 1-.57 1.696-.563.695-1.571.945 1.14.266 1.773 1.04.641.773.641 1.89 0 1.695-1.04 2.602-1.03.906-2.96.906t-2.969-.906Q6 26.738 6 25.043q0-1.117.64-1.89.641-.774 1.782-1.04zm-.578-2.492q0 .906.562 1.414.57.508 1.594.508 1.016 0 1.586-.508.578-.508.578-1.414 0-.906-.578-1.414-.57-.508-1.586-.508-1.023 0-1.594.508-.562.508-.562 1.414z" /></g><g transform="translate(375, 20) scale(0.75, 0.75)" fill="#e5e5e5" stroke="#e5e5e5"><path d="M10 22.785q-1.125 0-1.773.602-.641.601-.641 1.656t.64 1.656q.649.602 1.774.602t1.773-.602q.649-.61.649-1.656 0-1.055-.649-1.656-.64-.602-1.773-.602zm-1.578-.672q-1.016-.25-1.586-.945-.563-.695-.563-1.695 0-1.399.993-2.211 1-.813 2.734-.813 1.742 0 2.734.813.993.812.993 2.21 0 1-.57 1.696-.563.695-1.571.945 1.14.266 1.773 1.04.641.773.641 1.89 0 1.695-1.04 2.602-1.03.906-2.96.906t-2.969-.906Q6 26.738 6 25.043q0-1.117.64-1.89.641-.774 1.782-1.04zm-.578-2.492q0 .906.562 1.414.57.508 1.594.508 1.016 0 1.586-.508.578-.508.578-1.414 0-.906-.578-1.414-.57-.508-1.586-.508-1.023 0-1.594.508-.562.508-.562 1.414z" /></g><rect x="15" y="330" width="45" height="45" class="square dark a1" stroke="none" fill="#d18b47" /><rect x="60" y="330" width="45" height="45" class="square light b1" stroke="none" fill="#ffce9e" /><rect x="105" y="330" width="45" height="45" class="square dark c1" stroke="none" fill="#d18b47" /><rect x="150" y="330" width="45" height="45" class="square light d1" stroke="none" fill="#ffce9e" /><rect x="195" y="330" width="45" height="45" class="square dark e1" stroke="none" fill="#d18b47" /><rect x="240" y="330" width="45" height="45" class="square light f1" stroke="none" fill="#ffce9e" /><rect x="285" y="330" width="45" height="45" class="square dark g1" stroke="none" fill="#d18b47" /><rect x="330" y="330" width="45" height="45" class="square light h1" stroke="none" fill="#ffce9e" /><rect x="15" y="285" width="45" height="45" class="square light a2" stroke="none" fill="#ffce9e" /><rect x="60" y="285" width="45" height="45" class="square dark b2" stroke="none" fill="#d18b47" /><rect x="105" y="285" width="45" height="45" class="square light c2" stroke="none" fill="#ffce9e" /><rect x="150" y="285" width="45" height="45" class="square dark d2" stroke="none" fill="#d18b47" /><rect x="195" y="285" width="45" height="45" class="square light e2" stroke="none" fill="#ffce9e" /><rect x="240" y="285" width="45" height="45" class="square dark f2" stroke="none" fill="#d18b47" /><rect x="285" y="285" width="45" height="45" class="square light g2" stroke="none" fill="#ffce9e" /><rect x="330" y="285" width="45" height="45" class="square dark h2" stroke="none" fill="#d18b47" /><rect x="15" y="240" width="45" height="45" class="square dark a3" stroke="none" fill="#d18b47" /><rect x="60" y="240" width="45" height="45" class="square light b3" stroke="none" fill="#ffce9e" /><rect x="105" y="240" width="45" height="45" class="square dark c3" stroke="none" fill="#d18b47" /><rect x="150" y="240" width="45" height="45" class="square light d3" stroke="none" fill="#ffce9e" /><rect x="195" y="240" width="45" height="45" class="square dark e3" stroke="none" fill="#d18b47" /><rect x="240" y="240" width="45" height="45" class="square light f3" stroke="none" fill="#ffce9e" /><rect x="285" y="240" width="45" height="45" class="square dark g3" stroke="none" fill="#d18b47" /><rect x="330" y="240" width="45" height="45" class="square light h3" stroke="none" fill="#ffce9e" /><rect x="15" y="195" width="45" height="45" class="square light a4" stroke="none" fill="#ffce9e" /><rect x="60" y="195" width="45" height="45" class="square dark b4" stroke="none" fill="#d18b47" /><rect x="105" y="195" width="45" height="45" class="square light c4" stroke="none" fill="#ffce9e" /><rect x="150" y="195" width="45" height="45" class="square dark d4" stroke="none" fill="#d18b47" /><rect x="195" y="195" width="45" height="45" class="square light e4" stroke="none" fill="#ffce9e" /><rect x="240" y="195" width="45" height="45" class="square dark f4" stroke="none" fill="#d18b47" /><rect x="285" y="195" width="45" height="45" class="square light g4" stroke="none" fill="#ffce9e" /><rect x="330" y="195" width="45" height="45" class="square dark h4" stroke="none" fill="#d18b47" /><rect x="15" y="150" width="45" height="45" class="square dark a5" stroke="none" fill="#d18b47" /><rect x="60" y="150" width="45" height="45" class="square light b5" stroke="none" fill="#ffce9e" /><rect x="105" y="150" width="45" height="45" class="square dark c5" stroke="none" fill="#d18b47" /><rect x="150" y="150" width="45" height="45" class="square light d5" stroke="none" fill="#ffce9e" /><rect x="195" y="150" width="45" height="45" class="square dark e5" stroke="none" fill="#d18b47" /><rect x="240" y="150" width="45" height="45" class="square light f5" stroke="none" fill="#ffce9e" /><rect x="285" y="150" width="45" height="45" class="square dark g5" stroke="none" fill="#d18b47" /><rect x="330" y="150" width="45" height="45" class="square light h5" stroke="none" fill="#ffce9e" /><rect x="15" y="105" width="45" height="45" class="square light a6" stroke="none" fill="#ffce9e" /><rect x="60" y="105" width="45" height="45" class="square dark b6" stroke="none" fill="#d18b47" /><rect x="105" y="105" width="45" height="45" class="square light c6" stroke="none" fill="#ffce9e" /><rect x="150" y="105" width="45" height="45" class="square dark d6" stroke="none" fill="#d18b47" /><rect x="195" y="105" width="45" height="45" class="square light e6" stroke="none" fill="#ffce9e" /><rect x="240" y="105" width="45" height="45" class="square dark f6" stroke="none" fill="#d18b47" /><rect x="285" y="105" width="45" height="45" class="square light g6" stroke="none" fill="#ffce9e" /><rect x="330" y="105" width="45" height="45" class="square dark h6" stroke="none" fill="#d18b47" /><rect x="15" y="60" width="45" height="45" class="square dark a7" stroke="none" fill="#d18b47" /><rect x="60" y="60" width="45" height="45" class="square light b7" stroke="none" fill="#ffce9e" /><rect x="105" y="60" width="45" height="45" class="square dark c7" stroke="none" fill="#d18b47" /><rect x="150" y="60" width="45" height="45" class="square light d7" stroke="none" fill="#ffce9e" /><rect x="150" y="60" width="45" height="45" stroke="none" fill="gray" /><rect x="195" y="60" width="45" height="45" class="square dark e7" stroke="none" fill="#d18b47" /><rect x="240" y="60" width="45" height="45" class="square light f7" stroke="none" fill="#ffce9e" /><rect x="285" y="60" width="45" height="45" class="square dark g7" stroke="none" fill="#d18b47" /><rect x="330" y="60" width="45" height="45" class="square light h7" stroke="none" fill="#ffce9e" /><rect x="15" y="15" width="45" height="45" class="square light a8" stroke="none" fill="#ffce9e" /><rect x="60" y="15" width="45" height="45" class="square dark b8" stroke="none" fill="#d18b47" /><rect x="105" y="15" width="45" height="45" class="square light c8" stroke="none" fill="#ffce9e" /><rect x="150" y="15" width="45" height="45" class="square dark d8" stroke="none" fill="#d18b47" /><rect x="195" y="15" width="45" height="45" class="square light e8" stroke="none" fill="#ffce9e" /><rect x="240" y="15" width="45" height="45" class="square dark f8" stroke="none" fill="#d18b47" /><rect x="285" y="15" width="45" height="45" class="square light g8" stroke="none" fill="#ffce9e" /><rect x="330" y="15" width="45" height="45" class="square dark h8" stroke="none" fill="#d18b47" /><use href="#white-rook" xlink:href="#white-rook" transform="translate(15, 330)" /><use href="#white-knight" xlink:href="#white-knight" transform="translate(60, 330)" /><use href="#white-bishop" xlink:href="#white-bishop" transform="translate(105, 330)" /><use href="#white-queen" xlink:href="#white-queen" transform="translate(150, 330)" /><use href="#white-king" xlink:href="#white-king" transform="translate(195, 330)" /><use href="#white-bishop" xlink:href="#white-bishop" transform="translate(240, 330)" /><use href="#white-knight" xlink:href="#white-knight" transform="translate(285, 330)" /><use href="#white-rook" xlink:href="#white-rook" transform="translate(330, 330)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(15, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(60, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(105, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(240, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(285, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(330, 285)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(150, 195)" /><use href="#white-pawn" xlink:href="#white-pawn" transform="translate(195, 195)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(150, 150)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(195, 150)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(15, 60)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(60, 60)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(105, 60)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(240, 60)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(285, 60)" /><use href="#black-pawn" xlink:href="#black-pawn" transform="translate(330, 60)" /><use href="#black-rook" xlink:href="#black-rook" transform="translate(15, 15)" /><use href="#black-knight" xlink:href="#black-knight" transform="translate(60, 15)" /><use href="#black-bishop" xlink:href="#black-bishop" transform="translate(105, 15)" /><use href="#black-queen" xlink:href="#black-queen" transform="translate(150, 15)" /><use href="#black-king" xlink:href="#black-king" transform="translate(195, 15)" /><use href="#black-bishop" xlink:href="#black-bishop" transform="translate(240, 15)" /><use href="#black-knight" xlink:href="#black-knight" transform="translate(285, 15)" /><use href="#black-rook" xlink:href="#black-rook" transform="translate(330, 15)" /><line x1="172.5" y1="82.5" x2="172.5" y2="134.25" stroke="#15781B" opacity="0.5019607843137255" stroke-width="9.0" stroke-linecap="butt" class="arrow" /><polygon points="172.5,168.0 189.375,134.25 155.625,134.25" fill="#15781B" opacity="0.5019607843137255" class="arrow" /></svg>
    # """)

    def onTaskFinished(self, question, content, record_id):
        if self.is_first == True:
            application = self.application
            agent_cfg = self.agent_cfg
            taskList = application.tasklist_list[agent_cfg.user_id]
            taskList.deselect_all_items()
            taskList.addItem(question.replace("\n", "")[:50], record_id, True)
            # new_item=taskList.addItem(question.replace("\n", "")[:50], record_id, True)
            # new_item.setSelected(True)
            first_toplevel_item = taskList.topLevelItem(0)
            first_subitem = first_toplevel_item.child(0)
            first_subitem.setSelected(True)

        self.is_first = False
        toggle_msg_loading_status(self.messageBrowser.page())
        browser_page = self.messageBrowser.page()
        # add_agent_reply_msg_to_message_window(browser_page,content)已经在agent中处理了
        self.messages.append({"role": "assistant", "content": content})
        if self.tab_plugin:
            self.tab_plugin.handle_received_message(self, content)
        #1.将附件列表添加到相应的附件列表全局变量中 2.将附件内容加入相应的问题附件内容 3.将附件全部清理掉
        # 4.将相关的知识召回列表添加到全局变量中 5.将相关的知识召回内容添加到全局变量中 6.清理此次相关的知识召回的信息
        self.messages_attachment_list[self.page_index-1] = self.current_attachment_list
        # self.messages_attachment_content[self.page_index-1] = self.current_attachment_content
        if self.history_mode_checkbox.isChecked()==True:
            self.set_selected_history_index(self.page_index, "checked")

        self.remove_all_attachments()

        self.stopButton.setVisible(False)
        self.sendButton.setVisible(True)


    def setOpenFileName(self):
        openFileNameLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "QFileDialog.getOpenFileName()", openFileNameLabel,
                                                  "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            openFileNameLabel = fileName
        print(openFileNameLabel)
        return openFileNameLabel

    def new_task_by_btn(self):
        application=self.application
        application.create_new_task_chat(self.agent)

    def add_attachment(self):
        openFilesPath = ""
        openFileNamesLabel = ""
        options = QFileDialog.Options()
        native = True
        filter_extensions = ("Text and Document Files (*.txt *.docx *.csv *.xlsx *.xls *.pptx *.pdf *.md *.html *.htm *.js);;"
                             "Image Files (*.png *.jpg *.bmp *.jpeg *.gif);;"
                             "Text Files (*.txt);;"
                             "Microsoft Word (*.docx);;"
                             "CSV Files (*.csv);;"
                             "Excel Files (*.xlsx);;"
                             "Excel 97-2003 (*.xls);;"
                             "PowerPoint Files (*.pptx);;"
                             "PDF Files (*.pdf);;"
                             "Markdown Files (*.md);;"
                             "HTML Files (*.html *.htm);;"
                             "SQL Files (*.sql);;"
                             "Markdown Files (*.md)")
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "QFileDialog.getOpenFileNames()", openFilesPath,
                                                filter_extensions, options=options)

        self.add_attachment_area(files)


    def opendialog_plugin_tool(self):
        pluginselectedList_tool = self.pluginselectedList_tool
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All_Tool(is_delete=0)

        model = QStandardItemModel()
        header = ["", "plugin_id", "名称", "运行模式", "版本", "功能描述", "插件调用指令", "操作"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {f"{agent.plugin_id}": agent for agent in agents}

        # Process selected items first according to the order in pluginselectedList
        for selected in pluginselectedList_tool:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.plugin_id),
                    create_item(agent.name),
                    create_item({"back_end": "后台运行", "show_by_ai_call": "AI调用时显示插件", "show_when_activate": "启用时显示插件"}.get(agent.run_mode, "后台运行")),
                    create_item(agent.version),
                    create_item(agent.description),
                    create_item(agent.instruction),
                    create_item("操作")
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)

                selected_items.append((agent, row_data))

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.plugin_id),
                create_item(agent.name),
                create_item({"back_end": "后台运行", "show_by_ai_call": "AI调用时显示插件", "show_when_activate": "启用时显示插件"}.get(agent.run_mode, "后台运行")),
                create_item(agent.version),
                create_item(agent.description),
                create_item(agent.instruction),
                create_item("操作")
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append((agent, row_data))

        # Combine selected and unselected items
        all_items = selected_items + unselected_items

        # Add items to the model
        for row, (agent, item_row) in enumerate(all_items):
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)


            # Placeholder for button, actual button will be inserted by delegate
            model.setItem(row, 7, QStandardItem())

        # Generate items_per_row based on the order of all_items
        items_per_row = {}
        for i, (agent, _) in enumerate(all_items):
            detail_json = json.loads(agent.detail)
            items_per_row[i] = detail_json.get("model_type", [])

        dialog = PluginFreezeTableDialogTool(model, items_per_row)

        button_delegate = ButtonDelegateTool(dialog.tableView, dialog)
        dialog.tableView.setItemDelegateForColumn(7, button_delegate)

        if dialog.exec_() == QDialog.Accepted:
            self.pluginselectedList_tool = dialog.getResult()
            print("self.pluginselectedList:", self.pluginselectedList_tool)
            print("self.pluginselectedListjoin:", ",".join(self.pluginselectedList_tool))
            self.plugin_tool_record_selected_list.clear()
            if self.pluginselectedList_tool:
                for plugin_id in self.pluginselectedList_tool:
                    record = query_PluginMng(plugin_id=plugin_id)
                    self.plugin_tool_record_selected_list.append(record)





    def opendialogplugin(self):
        pluginselectedList = self.pluginselectedList
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All(is_delete=0,plugin_type="LLM_Connector")
        model = QStandardItemModel()
        header = ["", "plugin_id", "名称", "简称", "型号", "版本", "功能描述", "操作"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {f"{agent.name}: {agent.version}": agent for agent in agents}

        # Process selected items first according to the order in pluginselectedList
        for selected in pluginselectedList:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.plugin_id),
                    create_item(agent.name),
                    create_item(agent.alias_name),
                    create_item(json.dumps(agent.detail)),  # Convert JSON to string
                    create_item(agent.version),
                    create_item(agent.description),
                    create_item("操作")
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)

                selected_items.append((agent, row_data))

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.plugin_id),
                create_item(agent.name),
                create_item(agent.alias_name),
                create_item(json.dumps(agent.detail)),  # Convert JSON to string
                create_item(agent.version),
                create_item(agent.description),
                create_item("操作")
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append((agent, row_data))

        # Combine selected and unselected items
        all_items = selected_items + unselected_items

        # Add items to the model
        for row, (agent, item_row) in enumerate(all_items):
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)

            # Create a combo box for '型号'
            combo_item = QStandardItem("gpt-3.5-turbo")
            model.setItem(row, 4, combo_item)

            # Placeholder for button, actual button will be inserted by delegate
            model.setItem(row, 7, QStandardItem())

        # Generate items_per_row based on the order of all_items
        items_per_row = {}
        for i, (agent, _) in enumerate(all_items):
            detail_json = json.loads(agent.detail)
            items_per_row[i] = detail_json.get("model_type", [])

        dialog = PluginFreezeTableDialog(model, items_per_row)

        combo_delegate = ComboBoxDelegate(items_per_row, dialog.tableView)
        dialog.tableView.setItemDelegateForColumn(4, combo_delegate)
        button_delegate = ButtonDelegate(dialog.tableView, dialog)
        dialog.tableView.setItemDelegateForColumn(7, button_delegate)

        if dialog.exec_() == QDialog.Accepted:
            self.pluginselectedList = dialog.getResult()
            print("self.pluginselectedList:", self.pluginselectedList)
            print("self.pluginselectedListjoin:", ",".join(self.pluginselectedList))
            update_AgentCfg(self.agent_cfg.id, plugins=",".join(self.pluginselectedList))
            self.agent.reset_cfg_plugin_llm()
            tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            tech_list.reload()
            self.set_messagebox_placeholder()


    def opendialogkm(self):
        kmselectedList = self.kmselectedList
        print(kmselectedList)
        selected_items = []
        unselected_items = []

        agents = query_KMCfg_All(is_delete=0,vectorization=1)
        model = QStandardItemModel()
        header = ["", "km_id", "名称", "简介", "标签", "路径"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {agent.name: agent for agent in agents}

        # Process selected items first according to the order in kmselectedList
        for selected in kmselectedList:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.km_id),
                    create_item(agent.name),
                    create_item(agent.memo),
                    create_item(agent.label),
                    create_item(agent.kmpath)
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)
                selected_items.append(row_data)

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.km_id),
                create_item(agent.name),
                create_item(agent.memo),
                create_item(agent.label),
                create_item(agent.kmpath)
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append(row_data)

        # Add selected items to model first
        row = 0
        for item_row in selected_items + unselected_items:
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)
            row += 1

        dialog = KmFreezeTableDialog(model)
        if dialog.exec_() == QDialog.Accepted:
            self.kmselectedList = dialog.getResult()
            print("self.kmselectedList", self.kmselectedList)
            print("self.kmselectedList:", ",".join(self.kmselectedList))
            update_AgentCfg(self.agent_cfg.id, kms=",".join(self.kmselectedList))
            self.agent.reload_agent_cfg()
            tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            tech_list.reload()

    def openLink(self, url):
        webbrowser.open(url.toString())


    def generate_imagebak(self,prompt, model="dall-e-3", n=1, size="1024x1024"):
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer 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"  # 确保你已设置环境变量 OPENAI_API_KEY
        }
        data = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            # 提取 URL 列表
            urls = [item['url'] for item in response_json.get('data', [])]
            return urls  # 返回生成的图像 URL 列表
        else:
            response.raise_for_status()  # 抛出错误以便调试



    def generate_image(self, prompt, model="dall-e-3", n=1, size="1024x1024"):
        #***dall-e-3的n必须是1
        openai.api_key = "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"
        response = openai.images.generate(
            model=model,
            prompt=prompt,
            n=n,
            size=size,
            response_format="url",
        )

        # 提取 URL 列表
        # urls = [data['url'] for data in response['data']]
        urls = [datum.url for datum in response.data]
        return urls  # 返回生成的图像 URL 列表


    def set_messagebox_placeholder(self):
        if len(self.pluginselectedList) > 0:
            pluginname = self.pluginselectedList[0]
            llm = global_plugin_list[pluginname]
            config = llm.get_config()
            modelname = config.get("model", "")
            modelname = pluginname + f"({modelname})"
            # self.messageEdit.setPlaceholderText("Powered by " + modelname)
            # self.model_label.setText("Powered by " + modelname)
            self.model_label.setText(modelname)

    def save_task_output(self,output):
        print("cjrok the task output:",output)
        question=self.task_command
        answer=output
        attachment_content_list = json.dumps(self.attachment_content_list, ensure_ascii=False)  # km部分已经在agent中进行了处理，添加进去了

        record_id=add_AgentTask(self.task_id, question, question, answer, self.modelname, self.agent_cfg.user_id, self.is_first, attachment_content_list)
        self.onTaskFinished(question, answer, record_id)
