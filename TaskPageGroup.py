import os
import time
import urllib
from datetime import datetime

import openai
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QDialog
from PyQt5.QtCore import QSettings, Qt, QUrl, QFile, QFileInfo, pyqtSignal
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem

from langchainhandler import getvectorkm_String
from ui.ui_TaskPageWidget import Ui_TaskPageWidget
import hashlib
import webbrowser
import http.client
import json
from pluginsmanager import PluginEngine

import argparse

from pluginsmanager import FileSystem

import urllib.request
import re

import sys
from PyQt5 import QtWidgets, QtGui, QtCore

sys.path.append("..")
sys.path.append("../..")
from kmselect import FreezeTableDialog as KmFreezeTableDialog
from pluginselect import FreezeTableDialog as PluginFreezeTableDialog, ComboBoxDelegate, ButtonDelegate
from pluginselect import FreezeTableDialog as PluginFreezeTableDialog
from db.DBFactory import add_KMCfg, query_KMCfg_All, update_KMCfg, delete_KMCfg, query_KMCfg
from db.DBFactory import add_PluginMng, query_PluginMng_All, update_PluginMng, delete_PluginMng, query_PluginMng
from db.DBFactory import add_AgentTaskMulti
from db.DBFactory import update_MutiAgentCfg
from db.DBFactory import update_AgentCfg,query_AgentCfg
from db.DBFactory import add_AgentTask
from globals import global_plugin_list, global_agent_list
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QDialog, QTreeWidgetItemIterator, QPlainTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from Agent import Agent
from agentgroup import AgentGroup
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, toggle_msg_loading_status, add_agent_reply_msg_to_message_window
from pluginsmanager.plugins_gui.tab_plugin import load_plugin

class AgentCommanderWorkerThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, agent_group, messages, agent_list_to_run_task, pluginname, vector_path, embedding_model_name, agentcfg, task_id, is_first, owner, browser_page, speaker, parent=None):
        super(AgentCommanderWorkerThread, self).__init__(parent)
        self.agent_group = agent_group
        self.agent_list_to_run_task = agent_list_to_run_task
        self.pluginname = pluginname
        self.vector_path = vector_path
        self.embedding_model_name = embedding_model_name
        self.agentcfg = agentcfg
        self.task_id = task_id
        self.is_first = is_first
        self.messages = messages
        self.owner = owner
        self.browser_page = browser_page
        self.speaker =speaker

    def run(self):
        agent_group = self.agent_group
        agent_list_to_run_task = self.agent_list_to_run_task
        agent_group.give_it_speaker(self.speaker)
        content = agent_group.ask_it_to_assign_task(self.messages, agent_list_to_run_task, self.browser_page)
        topic = ""
        add_AgentTaskMulti(self.task_id, topic, content, self.owner, self.agentcfg.group_id, self.is_first)
        self.finished.emit(content)


class AgentWorkerThread(QThread):
    finished = pyqtSignal(str, str)

    def __init__(self, task_page_group, agent, task_index_to_run, task_content_to_run, agentcfg, task_id, is_first, messages, owner, browser_page, parent=None):
        super(AgentWorkerThread, self).__init__(parent)
        self.agent = agent
        self.task_index_to_run = task_index_to_run
        self.task_content_to_run = task_content_to_run
        self.task_page_group = task_page_group
        self.agentcfg = agentcfg
        self.task_id = task_id
        self.is_first = is_first
        self.messages = messages
        self.owner = owner
        self.browser_page = browser_page

    def run(self):
        agent = self.agent
        task_page_group = self.task_page_group
        content = agent.run_group_task(task_page_group, self.task_index_to_run, self.task_content_to_run, self.messages, self.browser_page)
        agent_name = agent.name
        task_index = self.task_index_to_run
        task_result = content
        topic = ""
        add_AgentTaskMulti(self.task_id, topic, content, self.owner, self.agentcfg.group_id, self.is_first)
        self.finished.emit(agent.name, content)
        task_page_group.signal_report_to_commander.emit(agent_name, task_index, task_result)


class TaskPageGroup(QWidget, Ui_TaskPageWidget):
    signal_report_to_commander = pyqtSignal(str, str, str)

    def __init__(self, application, agent_multi_cfg):
        super(TaskPageGroup, self).__init__()
        self.agent_multi_cfg = agent_multi_cfg
        self.name = agent_multi_cfg.name
        self.application = application
        self.task_id = ""
        self.is_first = True
        self.task_type = 'group'

        self.page_index = 0
        self.messages = [{"role": "system", "content": "You are a helpful assistant who provides concise and accurate information."}]
        self.task_command = ""

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

        self.conten_menu_closing = False  # 是否正在关闭内容菜单，用于给全选按钮做判断条件

        self.setupUi(self)

        self.messageEdit.setFocus()
        self.messageEdit.installEventFilter(self)
        # Example list of people
        self.personList = [query_AgentCfg(user_id=agent).name for agent in agent_multi_cfg.agents.split(",")]


        self.completer = QtWidgets.QCompleter(self.personList, self)
        self.completer.setWidget(self.messageEdit)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.completer.activated.connect(self.insertCompletion)

        self.sendButton.clicked.connect(self.sendMessage_click)
        self.llm_button.clicked.connect(self.opendialogplugin)
        self.newButton.clicked.connect(self.new_task_by_btn)
        self.attach_button.clicked.connect(self.add_attachment)
        self.kmButton.clicked.connect(self.opendialogkm)
        self.kmselectedList = []
        if agent_multi_cfg.kms != "":
            self.kmselectedList = agent_multi_cfg.kms.split(",")
        print(self.kmselectedList)
        self.pluginselectedList = []
        if agent_multi_cfg.plugins != "":
            self.pluginselectedList = agent_multi_cfg.plugins.split(",")
        print(self.pluginselectedList)
        agent = global_agent_list["001"]  # Altman
        self.Agent = agent

        agent_musk = global_agent_list["002"]  # Musk
        self.Agent_Musk = agent_musk

        self.agent_group = AgentGroup(agent_multi_cfg)

        self.signal_report_to_commander.connect(self.report_to_commander)

        self.is_browser_page_loaded = False
        self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

        # self.messageBrowser.anchorClicked.connect(self.openLink)

    # def eventFilter(self, obj, event):
    #     if obj == self.messageEdit and event.type() == QtCore.QEvent.KeyPress:
    #         if event.text() == "@":
    #             cursor = self.messageEdit.textCursor()
    #             rect = self.messageEdit.cursorRect(cursor)
    #             rect.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
    #             self.completer.complete(rect)  # Show completer popup
    #     return super().eventFilter(obj, event)
    #
    # def insertCompletion(self, completion):
    #     cursor = self.messageEdit.textCursor()
    #     cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, 1)  # Select the '@'
    #     cursor.insertText("@" + completion + " ")  # Insert '@' and the completion text
    #     self.messageEdit.setTextCursor(cursor)

    def eventFilter(self, obj, event):
        """过滤事件以检测 '@' 键的按下，并显示选择对话框"""
        if obj == self.messageEdit and event.type() == QtCore.QEvent.KeyPress:
            # if event.text() == "@":  # 检测 '@' 键
            if event.text() == "@" or (event.key() == QtCore.Qt.Key_Slash and event.modifiers() == QtCore.Qt.ControlModifier):
                self.showCompletionDialog()  # 显示选择对话框
                return True  # 事件被处理，返回True
        return super().eventFilter(obj, event)  # 其他事件交给基类处理

    def showCompletionDialog(self):
        """显示对话框，供用户选择内容"""
        choices = self.personList  # 选择项列表

        # 创建QDialog作为对话框
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("选择成员")  # 对话框标题

        layout = QtWidgets.QVBoxLayout(dialog)  # 创建布局
        list_widget = QtWidgets.QListWidget(dialog)  # 创建QListWidget显示选择项
        list_widget.addItems(choices)  # 添加选择项到QListWidget
        layout.addWidget(list_widget)  # 将QListWidget添加到布局

        # 连接选择项点击事件
        list_widget.itemClicked.connect(lambda item: self.insertCompletion(item.text(), dialog))
        # 连接键盘事件，以处理回车键
        list_widget.keyPressEvent = lambda event: self.handleKeyPress(event, list_widget, dialog)
        # 获取光标位置并设置对话框位置
        cursor = self.messageEdit.textCursor()  # 获取当前光标
        cursorRect = self.messageEdit.cursorRect(cursor)  # 获取光标的矩形区域
        # 计算对话框位置为光标的右上方

        # 将光标位置转换为全局坐标
        global_position = self.messageEdit.mapToGlobal(QtCore.QPoint(cursorRect.right(), cursorRect.top() - dialog.sizeHint().height()))
        dialog.move(global_position.x(), global_position.y())  # 设置对话框位置

        dialog.exec_()  # 显示对话框并等待用户操作

    def handleKeyPress(self, event, list_widget, dialog):
        """处理键盘事件，特别是回车键"""
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            # 获取当前选中的项
            current_item = list_widget.currentItem()
            if current_item:
                # 如果有选中的项，则插入内容并关闭对话框
                self.insertCompletion(current_item.text(), dialog)
        else:
            # 调用基类的keyPressEvent以处理其他按键
            super(QtWidgets.QListWidget, list_widget).keyPressEvent(event)

    def insertCompletion(self, completion, dialog):
        """插入用户选择的内容并关闭对话框"""
        cursor = self.messageEdit.textCursor()  # 获取当前光标
        # cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, 1)  # 选择 '@'
        cursor.insertText("@" + completion + " ")  # 插入 '@' 和选择的文本
        self.messageEdit.setTextCursor(cursor)  # 更新光标位置
        dialog.accept()  # 关闭对话框

    def onLoadFinished(self):
        self.is_browser_page_loaded = True

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

    def add_selected_history_index(self, i):
        # Check if 'i' is already in 'self.selected_history_index'
        if i not in self.selected_history_index:
            # Insert 'i' into 'self.selected_history_index' in sorted order
            self.selected_history_index.append(i)
            self.selected_history_index.sort()


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



    def edit_selected_content(self, code_type, text):
        tabs = self.tabWidget
        if code_type.lower() == "markdown" and "```mermaid" in text:
            text=text.replace("```mermaid","")
            print("mermaid")
            editor = tabs.findChild(QPlainTextEdit, "mermaid_editor")
            if editor is None:
                load_plugin(tabs, "Mermaid", "mermaid_editor", "MermaidEditor", content=text)
            else:
                editor.setPlainText(text)

        elif code_type.lower() == "markdown" and (("思维导图" in text and "##" in text) or ("mindmap" in text and "##" in text)) :

            print("mindmap")
            editor = tabs.findChild(QPlainTextEdit, "mindmap_editor")
            if editor is None:
                load_plugin(tabs, "MindMap", "mindmap_editor", "MindMapEditor", content=text)
            else:
                editor.setPlainText(text)
        else:

            editor=tabs.findChild(QPlainTextEdit,"code_editor")
            if editor is None:
                load_plugin(tabs,"编辑器","code_editor","CodeEditor",content=text)
            else:
                editor.setPlainText(text)

        if not self.output_checkbox.isChecked():
            self.output_checkbox.setChecked(True)
            self.toggle_output_checkbox(self.output_checkbox.checkState())


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
        self.messages = [{"role": "system", "content": "You are a helpful assistant who provides concise and accurate information."}]
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

    def sendMessage_click(self):
        if self.messageEdit.toPlainText():
            task_id = self.task_id
            topic = self.messageEdit.toPlainText()
            content = self.messageEdit.toPlainText()
            owner = "用户"
            agentcfg = self.agent_multi_cfg
            group_id = agentcfg.group_id
            application = self.application
            taskList = application.tasklist_group_list[agentcfg.group_id]

            if task_id == "":
                task_id = generate_random_id()
                self.task_id = task_id

            record_id = add_AgentTaskMulti(task_id, topic, content, owner, group_id, self.is_first)

            if self.is_first:
                taskList.addItem(topic.replace("\n", "")[:50], record_id, True)

            self.is_first = False


            if self.speaker.status == "wait_for_feedback":
                 self.speaker.human_feedback=self.messageEdit.toPlainText()
                 question=self.speaker.human_feedback
                 page_index = self.increment_page_index()
                 message = get_user_ask_msg_title_formatted(page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)

                 message = get_user_ask_msg_content_formatted(question)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 2)
                 self.messageBrowser.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

                 page_index = self.increment_page_index()
                 modelname="gpt4ooo"
                 message = get_agent_reply_msg_title_formatted(modelname, page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)
            else:
                self.sendMessage_to_AgentCommander(self.messageEdit.toPlainText())
            self.messageEdit.clear()

    def sendMessage_to_AgentCommanderbak(self, task_content):
        if task_content:
            # message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
            # message = f"""{task_content}"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

            page_index = self.increment_page_index()
            message = get_user_ask_msg_title_formatted(page_index)

            add_msg_to_message_window(self.messageBrowser.page(), message, 1)
            message = get_user_ask_msg_content_formatted(task_content)
            add_msg_to_message_window(self.messageBrowser.page(), message, 2)

            if len(self.pluginselectedList) > 0:
                pluginname = self.pluginselectedList[0]
                # modelname = self.pluginselectedList[0]

            else:
                pluginname = "ChatGLM连接器: 1.0.0"
                # modelname = "ChatGLM"

            if len(self.kmselectedList) > 0:
                vector_path = self.kmselectedList[0]
                vector_path = "vector_store"  # 先写死
                embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
            else:
                vector_path = ""
                embedding_model_name = ""

            agent = self.Agent
            agent.give_it_plugin(pluginname)
            agent.give_it_km(vector_path, embedding_model_name)

            modelname = agent.name

            pluginname = "百川连接器: 1.0.0"
            agent_musk = self.Agent_Musk
            agent_musk.give_it_plugin(pluginname)
            agent_musk.give_it_km(vector_path, embedding_model_name)

            # agent_list_to_run_task = {}
            # agent_list_to_run_task[agent.name] = agent
            # agent_list_to_run_task[agent_musk.name] = agent_musk

            # message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>(群主){self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}&nbsp;&nbsp;&nbsp;&nbsp;<img class='imgcls' style='width: 15px; height: 15px;' src='data:image/gif;base64,R0lGODlhDAAMAPcAAGi77nPA8H3E8X3F8YHG8YnK8orL8ozL8pDN85LO85fQ9JjR9JrS9J7T9KHV9aXW9anY9avZ9q3a9rDb97Hc9rLc97Pc97Pd97Td97nf97vg97zh+L7i+MDj+MHj+MPk+MTl+MTl+cXl+cfm+cjm+cnn+crn+cvn+czo+czo+tDq+tHq+tLr+tPs+dTs+tXs+tXs+9bt+9jt+9ju+9nu+9ru+9zv+97w/N/x++Dw/ODx/OLy/OTz/Of0/Oj1/On1/er1/Or2/ev2/ez2/ez3/e33/e73/e74/e/4/fD4/fH5/fL5/fL6/fP5/fT6/vX7/vb8/vf7//f8/vj8/vz9/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQJAwBVACwAAAAADAAMAAAIkwCrVFlRoYoUKVWWIBRYRQSBGAenBHki8IUJJA4eMIGSJAkVJU4yHIBAYcCHI0CK+NBBpEoNCQUEJGiBA8cPihYsTEAAQCAIGDl06Mg5QUEAgRdS3BBaRceGBgwMLNBQooaRhg4yhIAgAQOHGTJO4LDhoomHDyNIsFARpccQgTQi8DBhQkiHHQyboqhCtwoNHwIDAgAh+QQJBABTACwAAAAADAAMAIdsve54wvCAxvGCx/GFyPKNzPKPzPOQzfOUz/OX0PSa0vSe0/Se1PWi1fWl1vWo2PWs2vat2vav2/aw2/ay3Pez3Pez3fe03fe13ve23ve53/e53/i74fe84fi/4vjD5PjE5PjE5PnG5fnH5fnH5vnI5vnK5/nL5/rL6PrM6PnN6PrO6fnP6frS6/rT6/rV7PrW7PrW7frY7fvZ7vva7vvb7vvb7/vd7/ve8Pvi8vzj8vzj8/zk8/zl8/zp9f3r9v3s9v3t9/3u9/3u+P3v+P3w+P3z+f7z+v70+v30+v71+v72+/73/P74/P/5/P76/f76/f/7/f/8/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IlACnTGmBYUqUKFOUOBEokAQBGQefDGEiMEaKIg4eLIFyxIgUI0o4HIBwYUCJJEKK/OAhZIqNCQUEJKChQweQJVMyZLCAAIBAEzN28OChs4KCAAI3tMgxdEoODw0WGGDgYcUNIlNKOOgwIgIFDR9q2GCRAwcMJCBEnEDxwkUTH0EE1pDQQ4UKICF4MHTKYopdlz4EBgQAIfkECQMARgAsAAAAAAwADACHPafqTK7rT7DrXbbtcb/vfMTwg8fyjMvyls/zodX1o9X0pdb1ptb2qNf1rdr2rtv2s933tNz2t9/3vOD3vOH4veH3vuL4w+P4w+T4xeX5xuX5y+j6zun6z+n60uv61Ov61ev61ez71uz61uz72Oz62O362u772+763e/73vD74fH84vL85PP86fT86fX86fX96vX86/X86/b86/b97Pb97ff97vf97/f+8Pj+8fj99Pr99Pr+9fr+9vv+9/v++Pv++fz++v3/+/3//P3+/f3//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAjRhR4cFIkSJGhAwRKBBHAIMIayA0wiKHEQQLDvbQYWRIEBEDEhgBcIOIDCMzUPgQ+ECAAgxAbJiwIZBDhw4XGghsEcOGTw5AM0QQeOKFT5pGLBCosCHEBwkpBKYoAMGIARAkGBgpMcGGix1GKGhIkWJEByNBwBrhccAIWSMOfjA0QmOF26gwLBoJCAAh+QQJAwBJACwAAAAADAAMAIdFq+tTsexWs+1juO55w/GDx/GKyvKTzvOa0fSk1fSn1vWp2Pas2PWs2fas2vax3Pez3fe03Pa33va33/e+4fe/4ffA4vjA4/jB4/jD5PjG5fnI5vnJ5vnO6frQ6vrR6vrS6vrU7PvY7frY7fvY7fzZ7vva7vvb7vrc7/vf8Pvg8fvg8fzh8fvi8vzj8vzk8/zl8/zq9fzs9vzs9v3t9/3v+P7w+P3x+P3x+f7y+f3y+f7z+f71+v71+/72+/74+/74/P75/P75/P/6/P77/f/8/f79/v79/v/+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiwCTJGkRIokFC0mKGBEo0EYAgwh3IBEIQ0cSBAsOBvmR5AiREQMSJAEQoYLFGi6ACHwgQAGDEzlU3BDo4cMHDQ4EyqiBo6eHnxskCEwxoycOgRgIXOhAYgQFFgJXFJiQxIAIEw2SoMhgI0YPgxxUqCgBIskQHgJ9HEgiNgkEIQyT0HjBVkWSGTkEBgQAIfkECQQASAAsAAAAAAwADACHS63rWbTtXbXtabvuf8XxicnykM3ymdH0ntP0qNf1qdf1rNn2r9r2sNv3tN33t973ud/3ut/3vOD4wuP4w+P3w+T4xOT5xeX5yOb4yeb5yef5zOj50Or60ur60+v61ez61uz62e362+372+783O783O/73e/73vD64PH84fH74/L85PP85fP85vT86PX96vb96/b97vf97/j+8Pj98fn+8vn98vn+8vr+8/r+9Pr+9fr+9fv+9vr+9vv99vv++fz++v3++/3//P3+/P3//P7//v7+/v7//v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAkSBR8QHJhAlIjBQRKJBGAIMIfzBsUQMJggUHhQxBcoRIiAEJkAB4MEEijhdABDoQoIDBiR4udgjs4MEDhgYCZ9zAwbODzwwSBKqQwROHQAsEKHAYQeLCCoEpCkRAYkCECQdIUGiwAUMHkgobVKgoAQJJEB8CeRwYqAIJBIkMY7BgiyRGDoEBAQAh+QQJAwBCACwAAAAADAAMAIdSsOxgt+5kue5wv/CHyfKQzfOY0fSg1PWi1fWs2fat2vav2vay3Paz3Pa33ve53va64Pi+4fi/4fi/4vjE5PjG5PjH5fjH5fnL5vnM5/nM6PnP6fnQ6vrT6vrU6/rV7PrX7fva7vvb7/vd7/ve7/zf7/vf8Pvg8fzh8fvj8vzk8vzk8/zl8/zn9Pzo9f3s9v3u9/3v9/3v+P3w+f7x+P3z+f3z+f70+f71+v71+/72+/73+/74/P/6/f76/f/7/f79/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IgwCFCFEBQggFCgITCqQRwCBChS1sCEGw4GDCIEBEDEggBMCDhzpm/BDoQIACBih6wOAh0MOHDxgaCLxxA4dNDzgzSBDYgoZNHAIvEKjQgUQJDS4EpigQQYiBEScgCFnBocYLHUIsbGDBwkQIIT92CNxxQAhXIRN8KJTRwiwLITFyCAwIACH5BAkDAEkALAAAAAAMAAwAhzel6Uar61m07Wa672u873bB8I3L85PO85bQ9J7T9KLV9KXW9abX9avY9bDb9rDc97Lc9rTc9rbe97ne9rvg97vg+L7h98Hj+MLj+MLj+cbl+Mbl+crm+Mrn+cvn+czn+M/p+tDp+dLq+tPr+9br+tbs+tft+tft+9jt+t3w/N7w/ODw/ODx/OLx++Lx/OPy/OXz/Of0/Oj0/On1/er1/Ov2/e32/e/3/fD4/fH5/vL5/vP5/fT5/vX6/vb7/vf7/vj7/vj8/vj8//r8/vr9/vv9//z9//3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkgYEiiQYNSUKwEChQxwCDCAPcEChjR5IFEA4qOCAQSYoCDpIIoDABQBIiPo4IrEDgQYQGFnwUEXjChIkPEgQG+cHzx4mfIDAIpMGjp8AOBjiQWOFiRA2BMBBkSJKARYsLSWKU6GHDRxIPImLEeKEiiREgAoUwyBojyYYhDJPgmME2SQ6vSQICACH5BAkEAEIALAAAAAAMAAwAhz2n6kyu62C37my873G/73zE8JXP9JbP853T9aXW9abW9qnY9a3a9q7b9bPd9rbe97jf97nf973h+L7i+L/j+MLj+Mbk+cbl+cjm+cnn+czn+c3o+c7p+s/p+tLq+tLr+tbs+9nu+9ru+93v+97w++Hx++Hx/OLx/OPy/OXz/ebz/Ob0/en1/On1/er1/Ov2/e72/O73/e/4/vD4/vH4/fL5/fP6/vT6/vb6/ff7/vj7/vn8/vr9//v8/vv9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIUIUSFCSIYMQj6YECjQxgCDCAPMEMjihpAFDw4mOMCQRAEHQgRQkABASBAgDCcQcAChQQUgQQSGmNkhgsAeO3LumBnCgwWBMHDoFMjBwAYRKAjGEKgCwQUhCk6kwCDkxYgcMnII6QCiRYsVJYT84CFQBwMhXoVo8MFQCA0XaFsIqaFVSEAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zlM3ymtH0m9LzodT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t973ueD3uuD3vOD3v+H3weL4weP4yef5y+f5z+n60Or60er60ev60ur60+v61Ov61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j97/j+8Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAnTiRkcJJhw5OSrgQKHBIAYMIB/gQeKOIEwgWDjpQ4ITHihYHKjghoCGDACcIAnwQuMEAhQsSEgBgIBDFiRMiMAiMkEOJTxRASXAQCASJTyUCQSwIoWIGDhZBBNJoMPRBjBoenPR4ceSHESciTOjQYQOGkyZLBCaZ4GSskxFMGDoRsqOtDidEjggMCAAh+QQJAwBJACwAAAAADAAMAIc6pulJretLretZtO1uvu55wvB/xfGJyfKVz/OXz/Oe0/Si1fSk1vWq2fas2fax3Pay3Paz3Pa03fe53va53/e74Pi84fe94ffA4vjB4/jE5PjE5PnM5/jN6PnR6vrU6vrU6/rU6/vV7PrW7PrX7frZ7vrc7/vd7/vd8Pvf8Pzg8fvh8fvj8vzn9Pzo9f3p9fzp9f3q9fzq9v3r9v3s9v3t9vzt9/3u9/3u+P3v9/3x+f7z+v70+v71+v31+v71+/72+/74/P75/P76/f78/f78/v78/v/9/v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IjACTJIFxIkmHDklEsBAokEcBgwgH6BA4w0eSBxYOOlCQJIeKFQcqJCGgIYOAJAgCeBC4wcCECxESAGAgEMWJEx8wCIRQ44hPFEBJcBDYo4jPIwJBLAiRQgYOFz8EymiAUEKLGCOS7JAxREeQJCNM2LBB40USJEYECqGQZGySEkQYJuFxo62NJECECAwIACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9JvR86LV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg97/i+MDi98Pj+MTk+Mbk+cfl+c/p+tDq+dHq+tPr+tfs+tft+9jt+9ns+tru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIsUWUGiiAYNRT6oECgwRwGDCAfcEOhiR5EHFA42UFCExokUBygUIYDBgoAiCAJ0EJjBwIQKERIAWCCQhAkTIC4IhECDIYmfITYI/EGEoUAPDDygeHEjhg+BLBxwKCKhhYwRRXbYEIKjRxERJGqIhVGEyBCBQUSKLVLiLEMdM4qs5QFEYEAAIfkECQMAQQAsAAAAAAwADACHSK3rVrPsWbTtZrrvfMPwhsjxjcvzltD0nNL0ntP0odT1pdb1qtj1sNv2stz2tt32t973uN73ud/3weP4wuP4w+P4xuX4xuX5yOX5yuf50er60+r61Ov61ez62O362u772+762+772+/73fD83vD84fH74fH84vH74vL84/L85PP85fL85fP85vT86/b97fb97ff98Pf98Pj98fn+8vn+8/n+8/r+9fr+9vv++fz++vz++v3++/3++/3//f7+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAgwRxYSKIBg1BPLAQKPBGAYMIB9AQ+AJHkAgUDjpYEGTGCRYHKAQhgOGCgCAIAnAQmMHAhAoSEgBgILAEChQfLAhUAIGCzxJAQWwQOGKC0QkCRTQIsSLGDRw9BMJ40CHIhBcyVATZgeNHjRxBSKSgQcOGDIFABOq4EIRskBY+GAbBMaPtxBw8BAYEACH5BAkDAEIALAAAAAAMAAwAh0+w61227WC37my874PH8ozL8pXP9J3T9aDU9KLV9aXV9anY9a7b9rbe97ff97ne97zg97zh97zh+MPj+MPk+MTk+cbl+Mbl+cjm+cnm+crm+czn+c7p+tPr+tbr+dbs+tjt+tru+9zv+97v+97w+9/x/ODw/OHx++Ly/OTz/Obz/Ob0/en1/ev2/Oz2/e33/e73/e/4/vD4/vH4/fL5/fP5/vP6/vT6/fT6/vX6/vb7/vf7/vn8/vr9//v9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIUIcYFCSIcOQkKoECgwRwGDCAfYEBhjhxAJFw42WCBkRgoVBy4IIaAhgwAhCAJ8EMjBwAQLERIAYCAwhU0RGgQqeFChp80UJTwINEGhKAWBJByMYIGDB5AgAmFAACEEg4waLYQEASIERw8hJ1bgwKHjBkOBPjZ0xSHkBVSGO2isFeLjh8CAACH5BAkEAEwALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pHN85PO85vS85zS9KLV9aPW9aTW9aXW9ajY9a3a9rHc97je9rng97zg+L7h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+crn+cvn+szo+c7p+c7p+s/p+tDq+tHq+tPr+tbt+9jt+9rt+tzv+97w+9/w++Hx++Hx/OLy/OTz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiNAJkwuQGDyYkTTFTQEChQCAKDCAv0ELhjCJMLHQ5OgMCER4waDDwwMSDiAwEmDQagEFgiwQYOFhwIiCBwhgwZK0IIfEBBg88ZQF2kEKhAQoajAltUeIFjCAgACwTqwKCCyQgfQHgwORCARJAjTGLYECLECBEmOVgITGKCCVkmPZYwZFLkh1shTJAoERgQACH5BAkDAEsALAAAAAAMAAwAhzqm6Umt61217Wm77m6+7nnC8JDN8pXP85nR9J/U9aLV9KXW9ajX9ajY9qrZ9qvZ9rHc9rTd97re97zh977h98Hi+MPk+MXl+cfl+cjm+cnn+cro+cvo+czo+c7o+s7p+s/p+dDo+tHp+dHq+tTr+tbs+tjt+9nt+tnu+t3v+97w/ODx++Dx/OHx++Ty/eTz/OXz/Ob0/Ob0/ej0/Oj0/en1/On1/er2/ez2/e73/e/3/fD5/vH5/vL5/fL5/vT6/vX6/fb6/vb7/vj8/vn8/vr9/vv9//z9/vz9//7+/v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJcsyQFjiQkTS1LYECgwCAKDCAv8EMhjyBILHQ5OgLCkR4wbDj4sMRDCA4ElDQacEEhCwQYOFRgIiCCQxowZLUQIfEAhg08aQF2oEJhAAoajAl9ckLGjCAgACwT60MBiSQkgQ4gsORBghBAjS2rgGDLkCJIlOlYIPIJiCdklWhnCFeLWopIkAgMCACH5BAkDAEsALAAAAAAMAAwAhy+h6D+o6kGp6VCw7GS57nC/8HXA8H/F8I/M85jR9JnR9J7T9J/U9aDU9aLU9ajY9anY9avZ9qzY9q7Z9bDb9rTd9rfe973h+L7h97/i+MDi+MTj+Mfl+Mrn+czo+c3o+M7o+c/p+c/p+tDp+tDq+tHq+tPq+tPr+tXs+tfs+tru+9vv+93v+9/w+9/x/ODx++Hx++Lz/OPx/OTz/Obz/Of0/Oj1/en0/Or1/er2/ev2/O33/e/4/e/4/vD4/fD4/vL5/vP5/fP5/vT6/vf7/vj7/vj8/vr8/vr9/vv9/v3+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJcs4VFjiQoVS1rgECiQSAODCA8MEQikyBIOIQ5mqLBESA0dFEosSWBihIElEQqsEJgCwgcQGyQQsCAQh00ZKARO0NChp00cNGIIdIChZweBNjzcEHJhgYAHAoOQmLGEhZEcAJYoGHCCSJIlO34gQcIAwRIfMAQqebFk7JIAPRguOUKkLZIlIlwIDAgAIfkECQQATAAsAAAAAAwADACHN6XpRqvrSK3rVrPsa7zvdsHwfMPwhsjxk87znNL0ntP0oNT0otX0pdb1ptf1q9n2r9v2sNv2sdv2tt32uN73u+D4wOL4wOP5wuP3wuP4x+X5y+f5zOj5zOj60On50en50er50ur60+r60+v71Ov61ez61ez71uz62e372+/73O/73fD84PH84fH84vH75PP85fP85vP85vT85/T86PT86fT96fX96/b97PX87Pb97fb97ff97/f98Pj98fn+8/n98/n+8/r+9fr+9vr++Pv++Pz/+fz++vz9+/3+/P3+/P3//f7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAmTDpYYOJChVMWtwQKLCIA4MIDwgRCMQIkw0hDmagwOQHjR0TSjBRYEKEASYQCqwQmCICiA8aIhCoIDCHzRgoBErAwKGnzRw1YAhscKGDUYE3RugYYmGBgAcChZyYweTFERwAmCQYQIKIkoFBkiRhgICJDxcCl8hgIpZJAB4MmSCx2NYDC4EBAQAh+QQJAwBFACwAAAAADAAMAIc9p+pMrutPsOtdtu1xv+98xPCDx/KMy/KWz/Og1PSj1fSl1vWm1vao1/Wt2vau2vaz3faz3fe03Pa33/e84Pe84fi+4vjC4/jD5PjG5fnL6PrO6frP6frS6/rU6/rV6/rV7PvW7PrW7PvX7PrZ7vva7vvb7vrd7/ve8Pvh8fzi8vzk8/zp9Pzp9fzp9f3q9fzr9fzr9vzr9v3s9v3t9/3u9/3v9/7w+P7x+P30+v30+v71+v72+/73+/74+/75/P76/f/7/f/8/f79/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiQCLFMHxoggKFEVUzBAo0IcDgwgP7BCoA0gRDiIOZqhQREeLGhRIFGEw4oOBIhEKIDQ4wQMIDRAIWBBYo6YLEwIlZODAs2YNGCwENriwoSjNEjh+YFAg4IHAHidkFIkxxAaAIgkGhAAipEgOHkSILEAwcIVAIjSKhC0S4AbDIkKCqCVSpEMKgQEBACH5BAkDAEkALAAAAAAMAAwAh0Wr61Ox7Faz7WO47nnD8YPH8YrK8pPO85rR9KTW9afW9anY9qzY9azZ9qza9rHb9rPd97Tc9rfe9rff977h97/h98Di+MHj+MPk+MXl+cjm+cnm+c7p+tDq+tHq+tLq+tTs+9jt+tjt+9jt/Nnu+9ru+9vu+tzv+9/w++Dx++Dx/OHx++Ly/OPy/OTz/OXz/Or1/Oz2/Oz2/e33/e/4/vD4/fH4/fH5/vL5/fL5/vP5/vT6/fX6/vX7/vb7/vj7/vj8/vn8/vn8//r8/vv9//z9/v3+/v3+//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkwSEjSYoUSVzMEChQCASDCA/4EMhjSJIPJA5usJCkB4waGE4kaVAihIEkEwqoELiCgogRHCYQuCDwhk0ZKARK0OChp80bNGIIdJChg1GBNlLsMMFAgYAHAoG0oJEkR4UIAJIkGCCCyJEkP4JYsLAAQdUXApHoSDI2SYAaDJMYKcKWIwgWAgMCACH5BAkEAEkALAAAAAAMAAwAh0ut61m07V217Wm77n/F8YnJ8pDN8pnR9J7T9KjY9qnX9azZ9q7a9bDb97Td97Xd97fe97nf97rf97vg97zg+MLj+MPk+MTk+cXl+cfl+Mnn+crn+czo+dDq+tLq+tPr+tXs+tbs+tnt+tvt+9vu/Nzu/Nzv+93v+97w+uDx/OHx++Py/OTz/OXz/Ob0/Oj1/er2/ev2/e73/e/4/vD4/fH5/vL5/fL5/vL6/vP6/vT6/vX6/vX7/vb6/vb7/vj8/fn8/vr9/vv9//z9/vz9//z+//7+/v7+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiJAJMk0SEjyYoVSVoUFJgESASDCA/0EOhDSJIQJg5ysJBkR4wbGlIkcXBihIEkEgqoEMgCQwkSHSYQuCAwh80ZCJNQ2PChp80cOGgIbJDBg1GBPF78QMFAgYAHAoPAyNGwAgQASRIMEFEESRIiQypUWIAgiQ0XDIEkEZskQA2GSYwcWVshCYicAQEAIfkECQMAQQAsAAAAAAwADACHUrDsYLfuZLnucL/wh8nykM3zmNH0oNT1otX1q9n2rdr2r9r2stv1s9z2uN/3ud72uuD4vuH3vuH4v+H4v+L4xOT4x+X4x+X5yuX5zOj5zej5z+n50Or60+r61Ov61ez61+372u772+/73e/73u/83+/73/D74PH84fH74/L85PL85PP85fP85/T86PX97Pb97vf97/f97/j98Pn+8fj98/n98/n+9Pn+9fr+9fv+9vv+9/v++Pz/+v3/+/3+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIMAgwTJESMICxZBWsgQKLAHBYMID+wQuMNHkBAmDm6wEETHixocVgSBcGKEgSASCqQQ6CJDCRIdIhC4IBCHTRotBE7Q8KGnTRw3bghsgMGDUYE8YPhAwUCBAAcCfczQIbDCAwBBEgwQ8QMIwwoVFiAIYiMnwyBggwSgcfZrhSAgVAgMCAAh+QQJAwBJACwAAAAADAAMAIc3pelGq+tZtO1muu9rvO92wfCNy/OTzvOW0PSe0/Si1fSl1vWm1/Wr2PWv2/aw3Pey3Pa03Pa23ve53va74Pe84Pe/4vjB4/jC4/fC4/jC4/nG5fjG5fnK5/nL5/nM5/nP6fnQ6fnS6vrT6/vW6/rW7PrX7frX7fvY7frd8Pze8Pzg8Pzg8fzi8fvi8fzj8vzl8/zn9Pzo9Pzp9f3q9fzr9v3t9v3v9/3w+P3x+f7y+f7z+f30+f71+v72+/73+/74+/74/P74/P/6/P76/f77/f/8/f/9/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhwCTJPGRI0mMGElm4BAocAgHgwgZCBEIxEgSFS8OivAw0EaPEggvtGCRIIkGBDAE1hjhYgUJDAY6CPxBkwcNgRlAmNhJk2YQgRI+nBgqsIgPCw0iPCBAQeARH0SSAJhQQUASBwVSIBF4QMGGDRAWJNkhQ+CNAEm+Jhmgg2ESFiHSbkiCImWSgAAh+QQJBABDACwAAAAADAAMAIc9p+pMrutgt+5svO9xv+98xPCVz/SWz/Od0/Wl1vWm1vap2PWt2vau2/Wz3faz3fe23ve43/e53/e94fi+4vi/4/jD5PjG5PnG5fjG5fnI5vnJ5/nM5/nO6frP6frS6vrS6/rW7PvZ7vva7vvd7/ve8Pvh8fvh8fzi8fzj8vzl8/3m8/zm9P3p9fzp9f3q9fzr9fzu9vzu9/3v+P7w+P7x+P3y+f3z+v70+v72+v33+/74+/75/P76/f/7/P77/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhQCHDNFhY4gLF0Ne1BAo8AcHgwgZ7BDYA8gQEywOhvAwcIYOEjCGaFCBQsGQDAhWCJQxYkWKERgMdBDIo2aOGAIvfBDBs2ZNHwIleOApQqCQIBYaRHBAgALDIEKGAJhQQcCQBwVKMDyQYMMGCAuG4GghkEaAIV6HDLjBcMgJEGg3DGkpMCAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zmtH0m9LzoNT0odT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t9/3ueD3uuD3vOD3v+H3weL4wuT5yef5yuf5y+f5z+n60Or60er60ur60uv60+v61Or61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j98Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAnTg5QsTJjh1OeAgRKJAJCYMIJyQRuKSJkxg3Dp4Q4cTIjyMwejj5YEPGAyccGtQQGKRFDhorOigIIVCJTSRABHIogaKnTSU6IgjEMCKFUYEMACyQcIGCgQ0CQQRA4ERABg0EnFQ44IKFyAQOPHiwAMFJERwCfQxwItZJgSEMnbwwwdaDExUzBAYEACH5BAkDAEgALAAAAAAMAAwAhzqm6Umt60ut61m07W6+7nnC8H/F8YnJ8pXP857T9KLV9KPU9aTW9arZ9qzZ9rHc9rLc9rPc9rTd97ne9rnf97rf97zh973h98Di+MHj+MTk+MXl+czn+M3o+c7o+tHq+tTr+tXs+tbs+tfs+tnu+tzv+93v+93w+9/w/ODx++Hx++Py/Of0/Oj1/en1/On1/er1/Or2/ev2/ez2/e32/O33/e73/e74/e/3/fH5/vP6/vT6/vX6/fX6/vX7/vb7/vj8/vn8/vr9/vz9/vz+/vz+//3+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJEgCfIDSY0aSGzsEChwCAmDCCkEEVjkCBIXMw6WEIEESA4hMXQgEQGDhQQkHRrEEOijxY0YKDwoACHQiE0iPARyGGGip00jNCAIxADihFGBDAAsiHBhgoENAj8EQIBEQAYNBJBUOKAiBQ4kCRx06GDhAZIeMgTmGICyA5ICCxmuCNEWiYkXAgMCACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9KLV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg977h+L/i+MDh98Pj+MTk+Mbl+cjm+c/p+tDq+dHq+tLq+tPr+tfs+tft+9nt+9ru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIsUAcKjSI0aRWboEChwSAmDCCkEaUikCIyDNUiIKNIDhxAbO4qMkNEiQhEODVgI9BHjxgsUHRZ8YCiQyA+BG0KY2MmQxgOBFz6QGCpQAQAFECpIMJBBoIcACIoIsICBQJEJB1KcoFEkAQMNGig4KLLDhcAbA4qALVIgB00VINRqKEJihcCAACH5BAkDAEIALAAAAAAMAAwAh0it61az7Fm07Wa673zD8IbI8Y3L85bQ9JzS9KHU9aXW9anY9qrY9bDb9rLc9rbd9rbe97je97nf98Hj+MLj+MLj+cPj+Mbl+Mbl+cjm+cvn+dHq+tPq+tTr+tXr+tXs+tjt+tnt+tvv+9zv+93w/N7w/OHx++Hx/OLx++Ly/OPy/OTz/OXy/OXz/Ob0/Ov2/e32/e33/fD3/fD4/fH5/vL5/vP5/vP6/vX6/vb7/vn8/vr8/vr9/vv9/vv9//3+/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiLAIUI6aFDSI0aQmjkECjwhwuDCDHsEBhE4IwbB1WUEKLDBpAcPISsmAFjgpAPD2II9JEDhwwWHhqIEDiBgk0SAjmMSMFzgk8ICQReCGGiqEAGABZIsDDBgAaBHQIgECIAQwYCQiocaIGChhAFDjZsoBBBSA4YAmsMECJWSAEcDIW0AMF2g5ATLwQGBAAh+QQJAwBDACwAAAAADAAMAIdPsOtdtu1gt+5svO+Dx/KMy/KVz/Sd0/Wg1PSl1fWp2PWt2fWu2/a23ve33/e43va84Pe84fe84fjD4/jD5PjE5PnG5fjG5fnI5vnJ5vnK5vnK5/nM5/nO6fnT6/rW6/nW7PrY7frZ7fva7vvc7/ve8Pvf8fzg8Pzh8fvi8vzk8/zm8/zm9P3p9f3r9vzs9v3t9/3u9/3v+P7w+P7x+P3y+f3z+f7z+v70+v30+v71+v72+/73+/75/P76/f/7/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhgCHDAHyY0iOHENq8BAoUAgMgwg5FGQ4BMeOgyxQDPGBMIiQIS5szMAwJASEGA2D9MjRQoSDEgIpVJh5QuAHEypyUtj5IIFADSRyqhDIAMCCCBYmGOggEEQABEMEZNhAYMiFAytU0BiioIEHDxckDOEhQ+CNAUO+Dimgg+KKEWk9DEnxQmBAACH5BAkEAEoALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pLN85PO85vS85zS9KHU9aPW9aTW9ajY9a3a9rDb9rHc97nf97ng97vf977h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+cnn+cvn+szo+c7p+c7p+s/p+tDq+tHq+dPr+tbt+9jt+9rt+tzv+97w/N/w++Hx++Tz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJUoQWJECRAgSnoMESgwyQ6DCE0cEcjihhIhRA7SeKGkyA8SAQ4o0eGDxwglKjDgELgAAIggNlZUaCEwgwYNEhQITNEChs8MQCk4EBhiRYyjAiMIgGCBw4YEJQSiGNBACYEPIgwo8cBgxgsdSh5MOHGiwwUlQXII3FFACVklCBAylKHC7QklLmoIDAgAIfkECQMASwAsAAAAAAwADACHOqbpSa3rXbXtabvubr7uecLwkM3yltD0mdH0n9T1otX0pNb1qNj2qtn2q9n2sdz2stv1tN33u9/3vOH3veD3weL4w+T4xeX5x+X5yOb5yef5yuj5y+j5zOj5zej5zuj6z+n50Oj60en50er61ez61uz62O372e362e763e/73vD84PH74PH84fH84fL85PL85PP85fP85vT86PT86PT96fX86fX96vb97Pb97vf97/f98Pn+8fn+8vn98vn+9Pr+9fr99vr+9vv++Pz++fz++v3++/3//P3+/P3//v7+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAlyxJomTJkCFLhBARyHDhwSUojghcoWMJkiMHcdRYYkTIiAAHlhAZAqTEEhYafAhcAABEkR0uLsAQiCFDBgkJBKp4MaMnhp8UHAgU0YKGUYERBECowGGDAhICTwxgsITAhxAGlnhocENGjyUPJpgw0cGCQR4CfxRYMnYJgiAMl9hIwdbEkhg5BAYEADsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='></span></em></strong><br>"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')
            page_index = self.increment_page_index()
            message = get_agent_reply_msg_title_formatted(f"(群主){self.tr(modelname)}", page_index)
            add_msg_to_message_window(self.messageBrowser.page(), message, 1)

            agent_commander = self.agent_group
            owner = f'(群主){self.tr(modelname)}'
            self.messages.append({"role": "user", "content": task_content})
            messages = self.messages  # 分开两行否则加不进去
            speaker = self.speaker
            agent_list_to_run_task=self.agent_multi_cfg.agents.split(',')

            self.thread = AgentCommanderWorkerThread(agent_commander, messages, agent_list_to_run_task, pluginname, vector_path, embedding_model_name, self.agent_multi_cfg, self.task_id, self.is_first, owner, self.messageBrowser.page(), speaker)
            self.thread.finished.connect(self.onTaskAssignFinished)
            self.thread.start()

            self.messageEdit.clear()

    def sendMessage_to_AgentCommander(self, task_content):
        if task_content:
            # message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
            # message = f"""{task_content}"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

            page_index = self.increment_page_index()
            message = get_user_ask_msg_title_formatted(page_index)

            add_msg_to_message_window(self.messageBrowser.page(), message, 1)
            message = get_user_ask_msg_content_formatted(task_content)
            add_msg_to_message_window(self.messageBrowser.page(), message, 2)

            if len(self.pluginselectedList) > 0:
                pluginname = self.pluginselectedList[0]
                # modelname = self.pluginselectedList[0]

            else:
                pluginname = "ChatGLM连接器: 1.0.0"
                # modelname = "ChatGLM"

            if len(self.kmselectedList) > 0:
                vector_path = self.kmselectedList[0]
                vector_path = "vector_store"  # 先写死
                embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
            else:
                vector_path = ""
                embedding_model_name = ""

            agent = self.Agent
            agent.give_it_plugin(pluginname)
            agent.give_it_km(vector_path, embedding_model_name)

            modelname = agent.name

            pluginname = "百川连接器: 1.0.0"
            agent_musk = self.Agent_Musk
            agent_musk.give_it_plugin(pluginname)
            agent_musk.give_it_km(vector_path, embedding_model_name)

            # agent_list_to_run_task = {}
            # agent_list_to_run_task[agent.name] = agent
            # agent_list_to_run_task[agent_musk.name] = agent_musk

            # message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>(群主){self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}&nbsp;&nbsp;&nbsp;&nbsp;<img class='imgcls' style='width: 15px; height: 15px;' src='data:image/gif;base64,R0lGODlhDAAMAPcAAGi77nPA8H3E8X3F8YHG8YnK8orL8ozL8pDN85LO85fQ9JjR9JrS9J7T9KHV9aXW9anY9avZ9q3a9rDb97Hc9rLc97Pc97Pd97Td97nf97vg97zh+L7i+MDj+MHj+MPk+MTl+MTl+cXl+cfm+cjm+cnn+crn+cvn+czo+czo+tDq+tHq+tLr+tPs+dTs+tXs+tXs+9bt+9jt+9ju+9nu+9ru+9zv+97w/N/x++Dw/ODx/OLy/OTz/Of0/Oj1/On1/er1/Or2/ev2/ez2/ez3/e33/e73/e74/e/4/fD4/fH5/fL5/fL6/fP5/fT6/vX7/vb8/vf7//f8/vj8/vz9/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQJAwBVACwAAAAADAAMAAAIkwCrVFlRoYoUKVWWIBRYRQSBGAenBHki8IUJJA4eMIGSJAkVJU4yHIBAYcCHI0CK+NBBpEoNCQUEJGiBA8cPihYsTEAAQCAIGDl06Mg5QUEAgRdS3BBaRceGBgwMLNBQooaRhg4yhIAgAQOHGTJO4LDhoomHDyNIsFARpccQgTQi8DBhQkiHHQyboqhCtwoNHwIDAgAh+QQJBABTACwAAAAADAAMAIdsve54wvCAxvGCx/GFyPKNzPKPzPOQzfOUz/OX0PSa0vSe0/Se1PWi1fWl1vWo2PWs2vat2vav2/aw2/ay3Pez3Pez3fe03fe13ve23ve53/e53/i74fe84fi/4vjD5PjE5PjE5PnG5fnH5fnH5vnI5vnK5/nL5/rL6PrM6PnN6PrO6fnP6frS6/rT6/rV7PrW7PrW7frY7fvZ7vva7vvb7vvb7/vd7/ve8Pvi8vzj8vzj8/zk8/zl8/zp9f3r9v3s9v3t9/3u9/3u+P3v+P3w+P3z+f7z+v70+v30+v71+v72+/73/P74/P/5/P76/f76/f/7/f/8/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IlACnTGmBYUqUKFOUOBEokAQBGQefDGEiMEaKIg4eLIFyxIgUI0o4HIBwYUCJJEKK/OAhZIqNCQUEJKChQweQJVMyZLCAAIBAEzN28OChs4KCAAI3tMgxdEoODw0WGGDgYcUNIlNKOOgwIgIFDR9q2GCRAwcMJCBEnEDxwkUTH0EE1pDQQ4UKICF4MHTKYopdlz4EBgQAIfkECQMARgAsAAAAAAwADACHPafqTK7rT7DrXbbtcb/vfMTwg8fyjMvyls/zodX1o9X0pdb1ptb2qNf1rdr2rtv2s933tNz2t9/3vOD3vOH4veH3vuL4w+P4w+T4xeX5xuX5y+j6zun6z+n60uv61Ov61ev61ez71uz61uz72Oz62O362u772+763e/73vD74fH84vL85PP86fT86fX86fX96vX86/X86/b86/b97Pb97ff97vf97/f+8Pj+8fj99Pr99Pr+9fr+9vv+9/v++Pv++fz++v3/+/3//P3+/f3//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAjRhR4cFIkSJGhAwRKBBHAIMIayA0wiKHEQQLDvbQYWRIEBEDEhgBcIOIDCMzUPgQ+ECAAgxAbJiwIZBDhw4XGghsEcOGTw5AM0QQeOKFT5pGLBCosCHEBwkpBKYoAMGIARAkGBgpMcGGix1GKGhIkWJEByNBwBrhccAIWSMOfjA0QmOF26gwLBoJCAAh+QQJAwBJACwAAAAADAAMAIdFq+tTsexWs+1juO55w/GDx/GKyvKTzvOa0fSk1fSn1vWp2Pas2PWs2fas2vax3Pez3fe03Pa33va33/e+4fe/4ffA4vjA4/jB4/jD5PjG5fnI5vnJ5vnO6frQ6vrR6vrS6vrU7PvY7frY7fvY7fzZ7vva7vvb7vrc7/vf8Pvg8fvg8fzh8fvi8vzj8vzk8/zl8/zq9fzs9vzs9v3t9/3v+P7w+P3x+P3x+f7y+f3y+f7z+f71+v71+/72+/74+/74/P75/P75/P/6/P77/f/8/f79/v79/v/+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiwCTJGkRIokFC0mKGBEo0EYAgwh3IBEIQ0cSBAsOBvmR5AiREQMSJAEQoYLFGi6ACHwgQAGDEzlU3BDo4cMHDQ4EyqiBo6eHnxskCEwxoycOgRgIXOhAYgQFFgJXFJiQxIAIEw2SoMhgI0YPgxxUqCgBIskQHgJ9HEgiNgkEIQyT0HjBVkWSGTkEBgQAIfkECQQASAAsAAAAAAwADACHS63rWbTtXbXtabvuf8XxicnykM3ymdH0ntP0qNf1qdf1rNn2r9r2sNv3tN33t973ud/3ut/3vOD4wuP4w+P3w+T4xOT5xeX5yOb4yeb5yef5zOj50Or60ur60+v61ez61uz62e362+372+783O783O/73e/73vD64PH84fH74/L85PP85fP85vT86PX96vb96/b97vf97/j+8Pj98fn+8vn98vn+8vr+8/r+9Pr+9fr+9fv+9vr+9vv99vv++fz++v3++/3//P3+/P3//P7//v7+/v7//v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAkSBR8QHJhAlIjBQRKJBGAIMIfzBsUQMJggUHhQxBcoRIiAEJkAB4MEEijhdABDoQoIDBiR4udgjs4MEDhgYCZ9zAwbODzwwSBKqQwROHQAsEKHAYQeLCCoEpCkRAYkCECQdIUGiwAUMHkgobVKgoAQJJEB8CeRwYqAIJBIkMY7BgiyRGDoEBAQAh+QQJAwBCACwAAAAADAAMAIdSsOxgt+5kue5wv/CHyfKQzfOY0fSg1PWi1fWs2fat2vav2vay3Paz3Pa33ve53va64Pi+4fi/4fi/4vjE5PjG5PjH5fjH5fnL5vnM5/nM6PnP6fnQ6vrT6vrU6/rV7PrX7fva7vvb7/vd7/ve7/zf7/vf8Pvg8fzh8fvj8vzk8vzk8/zl8/zn9Pzo9f3s9v3u9/3v9/3v+P3w+f7x+P3z+f3z+f70+f71+v71+/72+/73+/74/P/6/f76/f/7/f79/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IgwCFCFEBQggFCgITCqQRwCBChS1sCEGw4GDCIEBEDEggBMCDhzpm/BDoQIACBih6wOAh0MOHDxgaCLxxA4dNDzgzSBDYgoZNHAIvEKjQgUQJDS4EpigQQYiBEScgCFnBocYLHUIsbGDBwkQIIT92CNxxQAhXIRN8KJTRwiwLITFyCAwIACH5BAkDAEkALAAAAAAMAAwAhzel6Uar61m07Wa672u873bB8I3L85PO85bQ9J7T9KLV9KXW9abX9avY9bDb9rDc97Lc9rTc9rbe97ne9rvg97vg+L7h98Hj+MLj+MLj+cbl+Mbl+crm+Mrn+cvn+czn+M/p+tDp+dLq+tPr+9br+tbs+tft+tft+9jt+t3w/N7w/ODw/ODx/OLx++Lx/OPy/OXz/Of0/Oj0/On1/er1/Ov2/e32/e/3/fD4/fH5/vL5/vP5/fT5/vX6/vb7/vf7/vj7/vj8/vj8//r8/vr9/vv9//z9//3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkgYEiiQYNSUKwEChQxwCDCAPcEChjR5IFEA4qOCAQSYoCDpIIoDABQBIiPo4IrEDgQYQGFnwUEXjChIkPEgQG+cHzx4mfIDAIpMGjp8AOBjiQWOFiRA2BMBBkSJKARYsLSWKU6GHDRxIPImLEeKEiiREgAoUwyBojyYYhDJPgmME2SQ6vSQICACH5BAkEAEIALAAAAAAMAAwAhz2n6kyu62C37my873G/73zE8JXP9JbP853T9aXW9abW9qnY9a3a9q7b9bPd9rbe97jf97nf973h+L7i+L/j+MLj+Mbk+cbl+cjm+cnn+czn+c3o+c7p+s/p+tLq+tLr+tbs+9nu+9ru+93v+97w++Hx++Hx/OLx/OPy/OXz/ebz/Ob0/en1/On1/er1/Ov2/e72/O73/e/4/vD4/vH4/fL5/fP6/vT6/vb6/ff7/vj7/vn8/vr9//v8/vv9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIUIUSFCSIYMQj6YECjQxgCDCAPMEMjihpAFDw4mOMCQRAEHQgRQkABASBAgDCcQcAChQQUgQQSGmNkhgsAeO3LumBnCgwWBMHDoFMjBwAYRKAjGEKgCwQUhCk6kwCDkxYgcMnII6QCiRYsVJYT84CFQBwMhXoVo8MFQCA0XaFsIqaFVSEAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zlM3ymtH0m9LzodT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t973ueD3uuD3vOD3v+H3weL4weP4yef5y+f5z+n60Or60er60ev60ur60+v61Ov61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j97/j+8Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAnTiRkcJJhw5OSrgQKHBIAYMIB/gQeKOIEwgWDjpQ4ITHihYHKjghoCGDACcIAnwQuMEAhQsSEgBgIBDFiRMiMAiMkEOJTxRASXAQCASJTyUCQSwIoWIGDhZBBNJoMPRBjBoenPR4ceSHESciTOjQYQOGkyZLBCaZ4GSskxFMGDoRsqOtDidEjggMCAAh+QQJAwBJACwAAAAADAAMAIc6pulJretLretZtO1uvu55wvB/xfGJyfKVz/OXz/Oe0/Si1fSk1vWq2fas2fax3Pay3Paz3Pa03fe53va53/e74Pi84fe94ffA4vjB4/jE5PjE5PnM5/jN6PnR6vrU6vrU6/rU6/vV7PrW7PrX7frZ7vrc7/vd7/vd8Pvf8Pzg8fvh8fvj8vzn9Pzo9f3p9fzp9f3q9fzq9v3r9v3s9v3t9vzt9/3u9/3u+P3v9/3x+f7z+v70+v71+v31+v71+/72+/74/P75/P76/f78/f78/v78/v/9/v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IjACTJIFxIkmHDklEsBAokEcBgwgH6BA4w0eSBxYOOlCQJIeKFQcqJCGgIYOAJAgCeBC4wcCECxESAGAgEMWJEx8wCIRQ44hPFEBJcBDYo4jPIwJBLAiRQgYOFz8EymiAUEKLGCOS7JAxREeQJCNM2LBB40USJEYECqGQZGySEkQYJuFxo62NJECECAwIACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9JvR86LV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg97/i+MDi98Pj+MTk+Mbk+cfl+c/p+tDq+dHq+tPr+tfs+tft+9jt+9ns+tru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIsUWUGiiAYNRT6oECgwRwGDCAfcEOhiR5EHFA42UFCExokUBygUIYDBgoAiCAJ0EJjBwIQKERIAWCCQhAkTIC4IhECDIYmfITYI/EGEoUAPDDygeHEjhg+BLBxwKCKhhYwRRXbYEIKjRxERJGqIhVGEyBCBQUSKLVLiLEMdM4qs5QFEYEAAIfkECQMAQQAsAAAAAAwADACHSK3rVrPsWbTtZrrvfMPwhsjxjcvzltD0nNL0ntP0odT1pdb1qtj1sNv2stz2tt32t973uN73ud/3weP4wuP4w+P4xuX4xuX5yOX5yuf50er60+r61Ov61ez62O362u772+762+772+/73fD83vD84fH74fH84vH74vL84/L85PP85fL85fP85vT86/b97fb97ff98Pf98Pj98fn+8vn+8/n+8/r+9fr+9vv++fz++vz++v3++/3++/3//f7+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAgwRxYSKIBg1BPLAQKPBGAYMIB9AQ+AJHkAgUDjpYEGTGCRYHKAQhgOGCgCAIAnAQmMHAhAoSEgBgILAEChQfLAhUAIGCzxJAQWwQOGKC0QkCRTQIsSLGDRw9BMJ40CHIhBcyVATZgeNHjRxBSKSgQcOGDIFABOq4EIRskBY+GAbBMaPtxBw8BAYEACH5BAkDAEIALAAAAAAMAAwAh0+w61227WC37my874PH8ozL8pXP9J3T9aDU9KLV9aXV9anY9a7b9rbe97ff97ne97zg97zh97zh+MPj+MPk+MTk+cbl+Mbl+cjm+cnm+crm+czn+c7p+tPr+tbr+dbs+tjt+tru+9zv+97v+97w+9/x/ODw/OHx++Ly/OTz/Obz/Ob0/en1/ev2/Oz2/e33/e73/e/4/vD4/vH4/fL5/fP5/vP6/vT6/fT6/vX6/vb7/vf7/vn8/vr9//v9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIUIcYFCSIcOQkKoECgwRwGDCAfYEBhjhxAJFw42WCBkRgoVBy4IIaAhgwAhCAJ8EMjBwAQLERIAYCAwhU0RGgQqeFChp80UJTwINEGhKAWBJByMYIGDB5AgAmFAACEEg4waLYQEASIERw8hJ1bgwKHjBkOBPjZ0xSHkBVSGO2isFeLjh8CAACH5BAkEAEwALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pHN85PO85vS85zS9KLV9aPW9aTW9aXW9ajY9a3a9rHc97je9rng97zg+L7h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+crn+cvn+szo+c7p+c7p+s/p+tDq+tHq+tPr+tbt+9jt+9rt+tzv+97w+9/w++Hx++Hx/OLy/OTz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiNAJkwuQGDyYkTTFTQEChQCAKDCAv0ELhjCJMLHQ5OgMCER4waDDwwMSDiAwEmDQagEFgiwQYOFhwIiCBwhgwZK0IIfEBBg88ZQF2kEKhAQoajAltUeIFjCAgACwTqwKCCyQgfQHgwORCARJAjTGLYECLECBEmOVgITGKCCVkmPZYwZFLkh1shTJAoERgQACH5BAkDAEsALAAAAAAMAAwAhzqm6Umt61217Wm77m6+7nnC8JDN8pXP85nR9J/U9aLV9KXW9ajX9ajY9qrZ9qvZ9rHc9rTd97re97zh977h98Hi+MPk+MXl+cfl+cjm+cnn+cro+cvo+czo+c7o+s7p+s/p+dDo+tHp+dHq+tTr+tbs+tjt+9nt+tnu+t3v+97w/ODx++Dx/OHx++Ty/eTz/OXz/Ob0/Ob0/ej0/Oj0/en1/On1/er2/ez2/e73/e/3/fD5/vH5/vL5/fL5/vT6/vX6/fb6/vb7/vj8/vn8/vr9/vv9//z9/vz9//7+/v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJcsyQFjiQkTS1LYECgwCAKDCAv8EMhjyBILHQ5OgLCkR4wbDj4sMRDCA4ElDQacEEhCwQYOFRgIiCCQxowZLUQIfEAhg08aQF2oEJhAAoajAl9ckLGjCAgACwT60MBiSQkgQ4gsORBghBAjS2rgGDLkCJIlOlYIPIJiCdklWhnCFeLWopIkAgMCACH5BAkDAEsALAAAAAAMAAwAhy+h6D+o6kGp6VCw7GS57nC/8HXA8H/F8I/M85jR9JnR9J7T9J/U9aDU9aLU9ajY9anY9avZ9qzY9q7Z9bDb9rTd9rfe973h+L7h97/i+MDi+MTj+Mfl+Mrn+czo+c3o+M7o+c/p+c/p+tDp+tDq+tHq+tPq+tPr+tXs+tfs+tru+9vv+93v+9/w+9/x/ODx++Hx++Lz/OPx/OTz/Obz/Of0/Oj1/en0/Or1/er2/ev2/O33/e/4/e/4/vD4/fD4/vL5/vP5/fP5/vT6/vf7/vj7/vj8/vr8/vr9/vv9/v3+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJcs4VFjiQoVS1rgECiQSAODCA8MEQikyBIOIQ5mqLBESA0dFEosSWBihIElEQqsEJgCwgcQGyQQsCAQh00ZKARO0NChp00cNGIIdIChZweBNjzcEHJhgYAHAoOQmLGEhZEcAJYoGHCCSJIlO34gQcIAwRIfMAQqebFk7JIAPRguOUKkLZIlIlwIDAgAIfkECQQATAAsAAAAAAwADACHN6XpRqvrSK3rVrPsa7zvdsHwfMPwhsjxk87znNL0ntP0oNT0otX0pdb1ptf1q9n2r9v2sNv2sdv2tt32uN73u+D4wOL4wOP5wuP3wuP4x+X5y+f5zOj5zOj60On50en50er50ur60+r60+v71Ov61ez61ez71uz62e372+/73O/73fD84PH84fH84vH75PP85fP85vP85vT85/T86PT86fT96fX96/b97PX87Pb97fb97ff97/f98Pj98fn+8/n98/n+8/r+9fr+9vr++Pv++Pz/+fz++vz9+/3+/P3+/P3//f7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAmTDpYYOJChVMWtwQKLCIA4MIDwgRCMQIkw0hDmagwOQHjR0TSjBRYEKEASYQCqwQmCICiA8aIhCoIDCHzRgoBErAwKGnzRw1YAhscKGDUYE3RugYYmGBgAcChZyYweTFERwAmCQYQIKIkoFBkiRhgICJDxcCl8hgIpZJAB4MmSCx2NYDC4EBAQAh+QQJAwBFACwAAAAADAAMAIc9p+pMrutPsOtdtu1xv+98xPCDx/KMy/KWz/Og1PSj1fSl1vWm1vao1/Wt2vau2vaz3faz3fe03Pa33/e84Pe84fi+4vjC4/jD5PjG5fnL6PrO6frP6frS6/rU6/rV6/rV7PvW7PrW7PvX7PrZ7vva7vvb7vrd7/ve8Pvh8fzi8vzk8/zp9Pzp9fzp9f3q9fzr9fzr9vzr9v3s9v3t9/3u9/3v9/7w+P7x+P30+v30+v71+v72+/73+/74+/75/P76/f/7/f/8/f79/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiQCLFMHxoggKFEVUzBAo0IcDgwgP7BCoA0gRDiIOZqhQREeLGhRIFGEw4oOBIhEKIDQ4wQMIDRAIWBBYo6YLEwIlZODAs2YNGCwENriwoSjNEjh+YFAg4IHAHidkFIkxxAaAIgkGhAAipEgOHkSILEAwcIVAIjSKhC0S4AbDIkKCqCVSpEMKgQEBACH5BAkDAEkALAAAAAAMAAwAh0Wr61Ox7Faz7WO47nnD8YPH8YrK8pPO85rR9KTW9afW9anY9qzY9azZ9qza9rHb9rPd97Tc9rfe9rff977h97/h98Di+MHj+MPk+MXl+cjm+cnm+c7p+tDq+tHq+tLq+tTs+9jt+tjt+9jt/Nnu+9ru+9vu+tzv+9/w++Dx++Dx/OHx++Ly/OPy/OTz/OXz/Or1/Oz2/Oz2/e33/e/4/vD4/fH4/fH5/vL5/fL5/vP5/vT6/fX6/vX7/vb7/vj7/vj8/vn8/vn8//r8/vv9//z9/v3+/v3+//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkwSEjSYoUSVzMEChQCASDCA/4EMhjSJIPJA5usJCkB4waGE4kaVAihIEkEwqoELiCgogRHCYQuCDwhk0ZKARK0OChp80bNGIIdJChg1GBNlLsMMFAgYAHAoG0oJEkR4UIAJIkGCCCyJEkP4JYsLAAQdUXApHoSDI2SYAaDJMYKcKWIwgWAgMCACH5BAkEAEkALAAAAAAMAAwAh0ut61m07V217Wm77n/F8YnJ8pDN8pnR9J7T9KjY9qnX9azZ9q7a9bDb97Td97Xd97fe97nf97rf97vg97zg+MLj+MPk+MTk+cXl+cfl+Mnn+crn+czo+dDq+tLq+tPr+tXs+tbs+tnt+tvt+9vu/Nzu/Nzv+93v+97w+uDx/OHx++Py/OTz/OXz/Ob0/Oj1/er2/ev2/e73/e/4/vD4/fH5/vL5/fL5/vL6/vP6/vT6/vX6/vX7/vb6/vb7/vj8/fn8/vr9/vv9//z9/vz9//z+//7+/v7+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiJAJMk0SEjyYoVSVoUFJgESASDCA/0EOhDSJIQJg5ysJBkR4wbGlIkcXBihIEkEgqoEMgCQwkSHSYQuCAwh80ZCJNQ2PChp80cOGgIbJDBg1GBPF78QMFAgYAHAoPAyNGwAgQASRIMEFEESRIiQypUWIAgiQ0XDIEkEZskQA2GSYwcWVshCYicAQEAIfkECQMAQQAsAAAAAAwADACHUrDsYLfuZLnucL/wh8nykM3zmNH0oNT1otX1q9n2rdr2r9r2stv1s9z2uN/3ud72uuD4vuH3vuH4v+H4v+L4xOT4x+X4x+X5yuX5zOj5zej5z+n50Or60+r61Ov61ez61+372u772+/73e/73u/83+/73/D74PH84fH74/L85PL85PP85fP85/T86PX97Pb97vf97/f97/j98Pn+8fj98/n98/n+9Pn+9fr+9fv+9vv+9/v++Pz/+v3/+/3+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIMAgwTJESMICxZBWsgQKLAHBYMID+wQuMNHkBAmDm6wEETHixocVgSBcGKEgSASCqQQ6CJDCRIdIhC4IBCHTRotBE7Q8KGnTRw3bghsgMGDUYE8YPhAwUCBAAcCfczQIbDCAwBBEgwQ8QMIwwoVFiAIYiMnwyBggwSgcfZrhSAgVAgMCAAh+QQJAwBJACwAAAAADAAMAIc3pelGq+tZtO1muu9rvO92wfCNy/OTzvOW0PSe0/Si1fSl1vWm1/Wr2PWv2/aw3Pey3Pa03Pa23ve53va74Pe84Pe/4vjB4/jC4/fC4/jC4/nG5fjG5fnK5/nL5/nM5/nP6fnQ6fnS6vrT6/vW6/rW7PrX7frX7fvY7frd8Pze8Pzg8Pzg8fzi8fvi8fzj8vzl8/zn9Pzo9Pzp9f3q9fzr9v3t9v3v9/3w+P3x+f7y+f7z+f30+f71+v72+/73+/74+/74/P74/P/6/P76/f77/f/8/f/9/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhwCTJPGRI0mMGElm4BAocAgHgwgZCBEIxEgSFS8OivAw0EaPEggvtGCRIIkGBDAE1hjhYgUJDAY6CPxBkwcNgRlAmNhJk2YQgRI+nBgqsIgPCw0iPCBAQeARH0SSAJhQQUASBwVSIBF4QMGGDRAWJNkhQ+CNAEm+Jhmgg2ESFiHSbkiCImWSgAAh+QQJBABDACwAAAAADAAMAIc9p+pMrutgt+5svO9xv+98xPCVz/SWz/Od0/Wl1vWm1vap2PWt2vau2/Wz3faz3fe23ve43/e53/e94fi+4vi/4/jD5PjG5PnG5fjG5fnI5vnJ5/nM5/nO6frP6frS6vrS6/rW7PvZ7vva7vvd7/ve8Pvh8fvh8fzi8fzj8vzl8/3m8/zm9P3p9fzp9f3q9fzr9fzu9vzu9/3v+P7w+P7x+P3y+f3z+v70+v72+v33+/74+/75/P76/f/7/P77/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhQCHDNFhY4gLF0Ne1BAo8AcHgwgZ7BDYA8gQEywOhvAwcIYOEjCGaFCBQsGQDAhWCJQxYkWKERgMdBDIo2aOGAIvfBDBs2ZNHwIleOApQqCQIBYaRHBAgALDIEKGAJhQQcCQBwVKMDyQYMMGCAuG4GghkEaAIV6HDLjBcMgJEGg3DGkpMCAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zmtH0m9LzoNT0odT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t9/3ueD3uuD3vOD3v+H3weL4wuT5yef5yuf5y+f5z+n60Or60er60ur60uv60+v61Or61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j98Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAnTg5QsTJjh1OeAgRKJAJCYMIJyQRuKSJkxg3Dp4Q4cTIjyMwejj5YEPGAyccGtQQGKRFDhorOigIIVCJTSRABHIogaKnTSU6IgjEMCKFUYEMACyQcIGCgQ0CQQRA4ERABg0EnFQ44IKFyAQOPHiwAMFJERwCfQxwItZJgSEMnbwwwdaDExUzBAYEACH5BAkDAEgALAAAAAAMAAwAhzqm6Umt60ut61m07W6+7nnC8H/F8YnJ8pXP857T9KLV9KPU9aTW9arZ9qzZ9rHc9rLc9rPc9rTd97ne9rnf97rf97zh973h98Di+MHj+MTk+MXl+czn+M3o+c7o+tHq+tTr+tXs+tbs+tfs+tnu+tzv+93v+93w+9/w/ODx++Hx++Py/Of0/Oj1/en1/On1/er1/Or2/ev2/ez2/e32/O33/e73/e74/e/3/fH5/vP6/vT6/vX6/fX6/vX7/vb7/vj8/vn8/vr9/vz9/vz+/vz+//3+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJEgCfIDSY0aSGzsEChwCAmDCCkEEVjkCBIXMw6WEIEESA4hMXQgEQGDhQQkHRrEEOijxY0YKDwoACHQiE0iPARyGGGip00jNCAIxADihFGBDAAsiHBhgoENAj8EQIBEQAYNBJBUOKAiBQ4kCRx06GDhAZIeMgTmGICyA5ICCxmuCNEWiYkXAgMCACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9KLV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg977h+L/i+MDh98Pj+MTk+Mbl+cjm+c/p+tDq+dHq+tLq+tPr+tfs+tft+9nt+9ru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIsUAcKjSI0aRWboEChwSAmDCCkEaUikCIyDNUiIKNIDhxAbO4qMkNEiQhEODVgI9BHjxgsUHRZ8YCiQyA+BG0KY2MmQxgOBFz6QGCpQAQAFECpIMJBBoIcACIoIsICBQJEJB1KcoFEkAQMNGig4KLLDhcAbA4qALVIgB00VINRqKEJihcCAACH5BAkDAEIALAAAAAAMAAwAh0it61az7Fm07Wa673zD8IbI8Y3L85bQ9JzS9KHU9aXW9anY9qrY9bDb9rLc9rbd9rbe97je97nf98Hj+MLj+MLj+cPj+Mbl+Mbl+cjm+cvn+dHq+tPq+tTr+tXr+tXs+tjt+tnt+tvv+9zv+93w/N7w/OHx++Hx/OLx++Ly/OPy/OTz/OXy/OXz/Ob0/Ov2/e32/e33/fD3/fD4/fH5/vL5/vP5/vP6/vX6/vb7/vn8/vr8/vr9/vv9/vv9//3+/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiLAIUI6aFDSI0aQmjkECjwhwuDCDHsEBhE4IwbB1WUEKLDBpAcPISsmAFjgpAPD2II9JEDhwwWHhqIEDiBgk0SAjmMSMFzgk8ICQReCGGiqEAGABZIsDDBgAaBHQIgECIAQwYCQiocaIGChhAFDjZsoBBBSA4YAmsMECJWSAEcDIW0AMF2g5ATLwQGBAAh+QQJAwBDACwAAAAADAAMAIdPsOtdtu1gt+5svO+Dx/KMy/KVz/Sd0/Wg1PSl1fWp2PWt2fWu2/a23ve33/e43va84Pe84fe84fjD4/jD5PjE5PnG5fjG5fnI5vnJ5vnK5vnK5/nM5/nO6fnT6/rW6/nW7PrY7frZ7fva7vvc7/ve8Pvf8fzg8Pzh8fvi8vzk8/zm8/zm9P3p9f3r9vzs9v3t9/3u9/3v+P7w+P7x+P3y+f3z+f7z+v70+v30+v71+v72+/73+/75/P76/f/7/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhgCHDAHyY0iOHENq8BAoUAgMgwg5FGQ4BMeOgyxQDPGBMIiQIS5szMAwJASEGA2D9MjRQoSDEgIpVJh5QuAHEypyUtj5IIFADSRyqhDIAMCCCBYmGOggEEQABEMEZNhAYMiFAytU0BiioIEHDxckDOEhQ+CNAUO+Dimgg+KKEWk9DEnxQmBAACH5BAkEAEoALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pLN85PO85vS85zS9KHU9aPW9aTW9ajY9a3a9rDb9rHc97nf97ng97vf977h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+cnn+cvn+szo+c7p+c7p+s/p+tDq+tHq+dPr+tbt+9jt+9rt+tzv+97w/N/w++Hx++Tz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJUoQWJECRAgSnoMESgwyQ6DCE0cEcjihhIhRA7SeKGkyA8SAQ4o0eGDxwglKjDgELgAAIggNlZUaCEwgwYNEhQITNEChs8MQCk4EBhiRYyjAiMIgGCBw4YEJQSiGNBACYEPIgwo8cBgxgsdSh5MOHGiwwUlQXII3FFACVklCBAylKHC7QklLmoIDAgAIfkECQMASwAsAAAAAAwADACHOqbpSa3rXbXtabvubr7uecLwkM3yltD0mdH0n9T1otX0pNb1qNj2qtn2q9n2sdz2stv1tN33u9/3vOH3veD3weL4w+T4xeX5x+X5yOb5yef5yuj5y+j5zOj5zej5zuj6z+n50Oj60en50er61ez61uz62O372e362e763e/73vD84PH74PH84fH84fL85PL85PP85fP85vT86PT86PT96fX86fX96vb97Pb97vf97/f98Pn+8fn+8vn98vn+9Pr+9fr99vr+9vv++Pz++fz++v3++/3//P3+/P3//v7+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAlyxJomTJkCFLhBARyHDhwSUojghcoWMJkiMHcdRYYkTIiAAHlhAZAqTEEhYafAhcAABEkR0uLsAQiCFDBgkJBKp4MaMnhp8UHAgU0YKGUYERBECowGGDAhICTwxgsITAhxAGlnhocENGjyUPJpgw0cGCQR4CfxRYMnYJgiAMl9hIwdbEkhg5BAYEADsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='></span></em></strong><br>"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')
            page_index = self.increment_page_index()
            message = get_agent_reply_msg_title_formatted(f"(群主){self.tr(modelname)}", page_index)
            add_msg_to_message_window(self.messageBrowser.page(), message, 1)

            agent_commander = self.agent_multi_cfg.agentcommander
            agent_group = self.agent_group
            owner = f'(群主){self.tr(modelname)}'
            self.messages.append({"role": "user", "content": task_content})
            messages = self.messages  # 分开两行否则加不进去
            speaker = self.speaker
            agent_list_to_run_task = self.agent_multi_cfg.agents.split(',')


            self.thread = AgentCommanderWorkerThread(agent_group, messages, agent_list_to_run_task, pluginname, vector_path, embedding_model_name, self.agent_multi_cfg, self.task_id, self.is_first, owner, self.messageBrowser.page(), speaker)
            self.thread.finished.connect(self.onTaskAssignFinished)
            self.thread.start()

            self.messageEdit.clear()

    def onTaskAssignFinished(self, content):
        # stoploadingstript = "var images = document.getElementsByClassName('imgcls');for (var i = 0; i < images.length; i++) { images[i].style.display = 'none';}"
        # self.messageBrowser.page().runJavaScript(stoploadingstript)
        # if content:
        #     message = content
        #
        #     text = message
        #
        #     # 使用正则表达式提取Python代码块
        #     python_code_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
        #     python_code_matches = python_code_pattern.findall(text)
        #
        #     # 打印提取的Python代码块
        #     python_code_list = []
        #
        #     for code_block in python_code_matches:
        #         python_code_list.append(code_block.strip())
        #
        #     # 打印结果
        #     print("Python代码列表:")
        #     i = 0
        #     s = text
        #
        #     answer_list = []
        #     type_list = []
        #     for code in python_code_list:
        #         print("python_code_list length", len(python_code_list))
        #         print("i:", i)
        #         print(code)
        #
        #         substring = code
        #         left_part = s[:s.find(substring)]
        #         right_part = s[s.find(substring) + len(substring):]
        #         print("左边所有字符:", left_part)
        #         print("右边所有字符:", right_part)
        #
        #         left_part = left_part[:left_part.find("```python")]
        #         right_part = right_part[right_part.find("```") + len("```"):]
        #         s = right_part
        #         answer_list.append(left_part.strip())
        #         type_list.append(0)
        #         answer_list.append(code)
        #         type_list.append(1)
        #
        #         i += 1
        #         if len(python_code_list) == i:
        #             answer_list.append(right_part.strip())
        #             type_list.append(0)
        #
        #     print("show all list *************************")
        #     j = 0
        #     scriptStr = ""
        #
        #     if len(answer_list) > 0:
        #         for answer in answer_list:
        #             print("*******", j, "***********")
        #             print("type_list:", type_list[j])
        #
        #             if type_list[j] == 1:
        #
        #                 copyhtml = """<div style="margin-top:15px;border:solid 0px red;width:100%;overflow: hidden; ">
        #                                 <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">代码类型:Python</span>
        #                                 <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
        #                             </div>""".format(j, j)
        #             else:
        #                 copyhtml = """<div style="border:solid 0px red;width:100%;overflow: hidden;display:none ">
        #                                 <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">Python</span>
        #                                 <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
        #                             </div>""".format(j, j)
        #
        #             print("copyhtml:", copyhtml)
        #             self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + copyhtml + '<br><br>`')
        #
        #             print(answer)
        #             message = answer
        #
        #             if type_list[j] == 1:
        #                 self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy" + str(j) + "' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
        #             else:
        #                 self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre id='codeToCopy" + str(j) + "' style='margin-top:-50px;border:solid 0px #c0c0c0;width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word;' class='language-python'></pre>\"")
        #
        #             message = message.replace('`', '\\`')
        #             message = f"""`{message}`"""
        #             self.messageBrowser.page().runJavaScript("$('#codeToCopy" + str(j) + "').html(" + message + ");")
        #             self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy" + str(j) + "'));")
        #
        #             # self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
        #             # self.messageBrowser.page().runJavaScript("$('#codeToCopy').html(" + message + ");")
        #             # #self.messageBrowser.page().runJavaScript("hljs.highlightAll();")
        #             # self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy'));")#$('#codeToCopy')
        #
        #             scriptStr = scriptStr + """
        #         document.getElementById('copyCodeLink{}').addEventListener('click', function (e) {{
        #             e.preventDefault();
        #             copyCode{}();
        #         }});
        #
        #         function copyCode{}() {{
        #             var code = document.getElementById('codeToCopy{}');
        #             var range = document.createRange();
        #             range.selectNode(code);
        #             window.getSelection().removeAllRanges();
        #             window.getSelection().addRange(range);
        #             document.execCommand('copy');
        #             window.getSelection().removeAllRanges();
        #             $("#yifuzhi{}").show();
        #             setTimeout(function () {{
        #             $("#yifuzhi{}").hide();
        #         }}, 1500);
        #         }}""".format(j, j, j, j, j, j)
        #             print("scripts:", scriptStr)
        #             # self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + message + '<br><br>`')
        #
        #             j += 1
        #     else:
        #         self.messageBrowser.page().runJavaScript('document.body.innerHTML += `<pre style="width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word; ">' + message + '</pre><br>`')
        #     if scriptStr != "":
        #         self.messageBrowser.page().runJavaScript(scriptStr)
        toggle_msg_loading_status(self.messageBrowser.page())
        self.signal_report_to_commander.emit("", "", "")

    def showTaskResult(self, agent_name, task_result):
        toggle_msg_loading_status(self.messageBrowser.page())

        # stoploadingstript = "var images = document.getElementsByClassName('imgcls');for (var i = 0; i < images.length; i++) { images[i].style.display = 'none';}"
        # self.messageBrowser.page().runJavaScript(stoploadingstript)

    #     message = task_result
    #
    #     text = message
    #
    #     # 使用正则表达式提取Python代码块
    #     python_code_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
    #     python_code_matches = python_code_pattern.findall(text)
    #
    #     # 打印提取的Python代码块
    #     python_code_list = []
    #
    #     for code_block in python_code_matches:
    #         python_code_list.append(code_block.strip())
    #
    #     # 打印结果
    #     print("Python代码列表:")
    #     i = 0
    #     s = text
    #
    #     answer_list = []
    #     type_list = []
    #     for code in python_code_list:
    #         print("python_code_list length", len(python_code_list))
    #         print("i:", i)
    #         print(code)
    #
    #         substring = code
    #         left_part = s[:s.find(substring)]
    #         right_part = s[s.find(substring) + len(substring):]
    #         print("左边所有字符:", left_part)
    #         print("右边所有字符:", right_part)
    #
    #         left_part = left_part[:left_part.find("```python")]
    #         right_part = right_part[right_part.find("```") + len("```"):]
    #         s = right_part
    #         answer_list.append(left_part.strip())
    #         type_list.append(0)
    #         answer_list.append(code)
    #         type_list.append(1)
    #
    #         i += 1
    #         if len(python_code_list) == i:
    #             answer_list.append(right_part.strip())
    #             type_list.append(0)
    #
    #     print("show all list *************************")
    #     j = 0
    #     scriptStr = ""
    #     if len(answer_list) > 0:
    #         for answer in answer_list:
    #             print("*******", j, "***********")
    #             print("type_list:", type_list[j])
    #
    #             if type_list[j] == 1:
    #
    #                 copyhtml = """<div style="margin-top:15px;border:solid 0px red;width:100%;overflow: hidden; ">
    #                         <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">代码类型:Python</span>
    #                         <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
    #                     </div>""".format(j, j)
    #             else:
    #                 copyhtml = """<div style="border:solid 0px red;width:100%;overflow: hidden;display:none ">
    #                         <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">Python</span>
    #                         <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
    #                     </div>""".format(j, j)
    #
    #             print("copyhtml:", copyhtml)
    #             self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + copyhtml + '<br><br>`')
    #
    #             print(answer)
    #             message = answer
    #
    #             if type_list[j] == 1:
    #                 self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy" + str(j) + "' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
    #             else:
    #                 self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre id='codeToCopy" + str(j) + "' style='margin-top:-50px;border:solid 0px #c0c0c0;width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word;' class='language-python'></pre>\"")
    #
    #             message = message.replace('`', '\\`')
    #             message = f"""`{message}`"""
    #             self.messageBrowser.page().runJavaScript("$('#codeToCopy" + str(j) + "').html(" + message + ");")
    #             self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy" + str(j) + "'));")
    #
    #             # self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
    #             # self.messageBrowser.page().runJavaScript("$('#codeToCopy').html(" + message + ");")
    #             # #self.messageBrowser.page().runJavaScript("hljs.highlightAll();")
    #             # self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy'));")#$('#codeToCopy')
    #
    #             scriptStr = scriptStr + """
    # document.getElementById('copyCodeLink{}').addEventListener('click', function (e) {{
    #     e.preventDefault();
    #     copyCode{}();
    # }});
    #
    # function copyCode{}() {{
    #     var code = document.getElementById('codeToCopy{}');
    #     var range = document.createRange();
    #     range.selectNode(code);
    #     window.getSelection().removeAllRanges();
    #     window.getSelection().addRange(range);
    #     document.execCommand('copy');
    #     window.getSelection().removeAllRanges();
    #     $("#yifuzhi{}").show();
    #     setTimeout(function () {{
    #     $("#yifuzhi{}").hide();
    # }}, 1500);
    # }}""".format(j, j, j, j, j, j)
    #             print("scripts:", scriptStr)
    #             # self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + message + '<br><br>`')
    #
    #             j += 1
    #     else:
    #         self.messageBrowser.page().runJavaScript('document.body.innerHTML += `<pre style="width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word; ">' + message + '</pre><br>`')
    #     if scriptStr != "":
    #         self.messageBrowser.page().runJavaScript(scriptStr)

    def sendMessage(self, question):
        print("sending")
        # messageBox = AutoCloseMessageBox()
        # messageBox.exec_()

        if question:

            __cli_args = self.__init_cli().parse_args()
            print("cjrok")
            print(__cli_args.log)
            print("cjrok2")
            # delegate = self.__init_app({
            #     'log_level': __cli_args.log,
            #     'directory': __cli_args.directory
            # })

            if len(self.pluginselectedList) > 0:
                pluginname = self.pluginselectedList[0]

                modelname = self.pluginselectedList[0]
            else:
                pluginname = "ChatGLM连接器: 1.0.0"
                modelname = "ChatGLM"

            promptstr = ""
            if len(self.kmselectedList) > 0:
                vector_path = self.kmselectedList[0]
                vector_path = "vector_store"  # 先写死
                embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
            else:
                vector_path = ""
                embedding_model_name = ""

            back_ground_knowledge = ""
            talk_template_common = f'请根据后面提供的背景内容回答问题，回答只能限制在背景内容的范围内，问题是：{question};供参考的背景内容是：{back_ground_knowledge}'

            agent = self.Agent
            agent.give_it_plugin(pluginname)
            agent.give_it_km(vector_path, embedding_model_name)
            content = agent.ask_it(question)
            modelname = agent.name

            agent_musk = self.Agent_Musk
            agent_musk.give_it_plugin(pluginname)
            agent_musk.give_it_km(vector_path, embedding_model_name)
            content_musk = agent_musk.ask_it(question)

            if question == "ymcymc":

                print(os.getcwd())
                print(os.path.join(os.getcwd(), "scripts", "index.html"))
                print(urllib.request.pathname2url(os.path.join(os.getcwd(), "index.html")))
                url_string = urllib.request.pathname2url(os.path.join(os.getcwd(), "scripts", "index.html"))
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("okcjrok")
            elif question == "szrszr":

                url_string = "https://bridge.yfd.net:1443/"
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("szrszr")

            else:

                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
                message = f"""{question}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

                message = content

                text = message

                # 使用正则表达式提取Python代码块
                python_code_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
                python_code_matches = python_code_pattern.findall(text)

                # 打印提取的Python代码块
                python_code_list = []

                for code_block in python_code_matches:
                    python_code_list.append(code_block.strip())

                # 打印结果
                print("Python代码列表:")
                i = 0
                s = text

                answer_list = []
                type_list = []
                for code in python_code_list:
                    print("python_code_list length", len(python_code_list))
                    print("i:", i)
                    print(code)

                    substring = code
                    left_part = s[:s.find(substring)]
                    right_part = s[s.find(substring) + len(substring):]
                    print("左边所有字符:", left_part)
                    print("右边所有字符:", right_part)

                    left_part = left_part[:left_part.find("```python")]
                    right_part = right_part[right_part.find("```") + len("```"):]
                    s = right_part
                    answer_list.append(left_part.strip())
                    type_list.append(0)
                    answer_list.append(code)
                    type_list.append(1)

                    i += 1
                    if len(python_code_list) == i:
                        answer_list.append(right_part.strip())
                        type_list.append(0)

                print("show all list *************************")
                j = 0
                scriptStr = ""
                if len(answer_list) > 0:
                    for answer in answer_list:
                        print("*******", j, "***********")
                        print("type_list:", type_list[j])

                        if type_list[j] == 1:

                            copyhtml = """<div style="margin-top:15px;border:solid 0px red;width:100%;overflow: hidden; ">
                            <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">代码类型:Python</span>
                            <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
                        </div>""".format(j, j)
                        else:
                            copyhtml = """<div style="border:solid 0px red;width:100%;overflow: hidden;display:none ">
                            <span href="#" class="codetype" id="codetype" style="float: left;text-decoration:none">Python</span>
                            <span style="float: right;"><span id="yifuzhi{}" style="font-size:10pt;color:red;display:none">已经复制到剪切板了&nbsp;&nbsp;&nbsp;&nbsp;</span><a href="#" class="copy-link" id="copyCodeLink{}">复制代码</a></span>
                        </div>""".format(j, j)

                        print("copyhtml:", copyhtml)
                        self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + copyhtml + '<br><br>`')

                        print(answer)
                        message = answer

                        if type_list[j] == 1:
                            self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy" + str(j) + "' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
                        else:
                            self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre id='codeToCopy" + str(j) + "' style='margin-top:-50px;border:solid 0px #c0c0c0;width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word;' class='language-python'></pre>\"")

                        message = message.replace('`', '\\`')
                        message = f"""`{message}`"""
                        self.messageBrowser.page().runJavaScript("$('#codeToCopy" + str(j) + "').html(" + message + ");")
                        self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy" + str(j) + "'));")

                        # self.messageBrowser.page().runJavaScript("document.body.innerHTML += " + "\"<pre style='margin-top:-50px'><code id='codeToCopy' style='border:solid 1px #c0c0c0' class='language-python'></code></pre>\"")
                        # self.messageBrowser.page().runJavaScript("$('#codeToCopy').html(" + message + ");")
                        # #self.messageBrowser.page().runJavaScript("hljs.highlightAll();")
                        # self.messageBrowser.page().runJavaScript("hljs.highlightBlock(document.getElementById('codeToCopy'));")#$('#codeToCopy')

                        scriptStr = scriptStr + """
    document.getElementById('copyCodeLink{}').addEventListener('click', function (e) {{
        e.preventDefault();
        copyCode{}();
    }});

    function copyCode{}() {{
        var code = document.getElementById('codeToCopy{}');
        var range = document.createRange();
        range.selectNode(code);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
        $("#yifuzhi{}").show();
        setTimeout(function () {{
        $("#yifuzhi{}").hide();
    }}, 1500);
    }}""".format(j, j, j, j, j, j)
                        print("scripts:", scriptStr)
                        # self.messageBrowser.page().runJavaScript('document.body.innerHTML += `' + message + '<br><br>`')

                        j += 1
                else:
                    self.messageBrowser.page().runJavaScript('document.body.innerHTML += `<pre style="width: 99%; paddingbak: 10px; white-space: pre-wrap; word-wrap: break-word;  overflow-wrap: break-word; ">' + message + '</pre><br>`')
                if scriptStr != "":
                    self.messageBrowser.page().runJavaScript(scriptStr)

            self.messageEdit.clear()

    def report_to_commander(self, agent_name, task_id, task_result):
        print("report ai_chat_cfg", agent_name)
        print("taks_id", task_id)
        print("taskresult", task_result)

        # if agent_name!="":
        # self.showTaskResult(agent_name, task_result)
        agent_commander = self.agent_group
        if len(agent_commander.task_list_to_run) > 0:
            task = agent_commander.task_list_to_run.pop(0)
            agent_name_to_run = task[0]
            task_id_to_run = task[1]
            task_content_to_run = task[2]
            agent = agent_commander.agent_list_to_run_task[agent_name_to_run]
            agent_name = agent.name
            # message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(agent_name)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}&nbsp;&nbsp;&nbsp;&nbsp;<img class='imgcls' style='width: 15px; height: 15px;' src='data:image/gif;base64,R0lGODlhDAAMAPcAAGi77nPA8H3E8X3F8YHG8YnK8orL8ozL8pDN85LO85fQ9JjR9JrS9J7T9KHV9aXW9anY9avZ9q3a9rDb97Hc9rLc97Pc97Pd97Td97nf97vg97zh+L7i+MDj+MHj+MPk+MTl+MTl+cXl+cfm+cjm+cnn+crn+cvn+czo+czo+tDq+tHq+tLr+tPs+dTs+tXs+tXs+9bt+9jt+9ju+9nu+9ru+9zv+97w/N/x++Dw/ODx/OLy/OTz/Of0/Oj1/On1/er1/Or2/ev2/ez2/ez3/e33/e73/e74/e/4/fD4/fH5/fL5/fL6/fP5/fT6/vX7/vb8/vf7//f8/vj8/vz9/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQJAwBVACwAAAAADAAMAAAIkwCrVFlRoYoUKVWWIBRYRQSBGAenBHki8IUJJA4eMIGSJAkVJU4yHIBAYcCHI0CK+NBBpEoNCQUEJGiBA8cPihYsTEAAQCAIGDl06Mg5QUEAgRdS3BBaRceGBgwMLNBQooaRhg4yhIAgAQOHGTJO4LDhoomHDyNIsFARpccQgTQi8DBhQkiHHQyboqhCtwoNHwIDAgAh+QQJBABTACwAAAAADAAMAIdsve54wvCAxvGCx/GFyPKNzPKPzPOQzfOUz/OX0PSa0vSe0/Se1PWi1fWl1vWo2PWs2vat2vav2/aw2/ay3Pez3Pez3fe03fe13ve23ve53/e53/i74fe84fi/4vjD5PjE5PjE5PnG5fnH5fnH5vnI5vnK5/nL5/rL6PrM6PnN6PrO6fnP6frS6/rT6/rV7PrW7PrW7frY7fvZ7vva7vvb7vvb7/vd7/ve8Pvi8vzj8vzj8/zk8/zl8/zp9f3r9v3s9v3t9/3u9/3u+P3v+P3w+P3z+f7z+v70+v30+v71+v72+/73/P74/P/5/P76/f76/f/7/f/8/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IlACnTGmBYUqUKFOUOBEokAQBGQefDGEiMEaKIg4eLIFyxIgUI0o4HIBwYUCJJEKK/OAhZIqNCQUEJKChQweQJVMyZLCAAIBAEzN28OChs4KCAAI3tMgxdEoODw0WGGDgYcUNIlNKOOgwIgIFDR9q2GCRAwcMJCBEnEDxwkUTH0EE1pDQQ4UKICF4MHTKYopdlz4EBgQAIfkECQMARgAsAAAAAAwADACHPafqTK7rT7DrXbbtcb/vfMTwg8fyjMvyls/zodX1o9X0pdb1ptb2qNf1rdr2rtv2s933tNz2t9/3vOD3vOH4veH3vuL4w+P4w+T4xeX5xuX5y+j6zun6z+n60uv61Ov61ev61ez71uz61uz72Oz62O362u772+763e/73vD74fH84vL85PP86fT86fX86fX96vX86/X86/b86/b97Pb97ff97vf97/f+8Pj+8fj99Pr99Pr+9fr+9vv+9/v++Pv++fz++v3/+/3//P3+/f3//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAjRhR4cFIkSJGhAwRKBBHAIMIayA0wiKHEQQLDvbQYWRIEBEDEhgBcIOIDCMzUPgQ+ECAAgxAbJiwIZBDhw4XGghsEcOGTw5AM0QQeOKFT5pGLBCosCHEBwkpBKYoAMGIARAkGBgpMcGGix1GKGhIkWJEByNBwBrhccAIWSMOfjA0QmOF26gwLBoJCAAh+QQJAwBJACwAAAAADAAMAIdFq+tTsexWs+1juO55w/GDx/GKyvKTzvOa0fSk1fSn1vWp2Pas2PWs2fas2vax3Pez3fe03Pa33va33/e+4fe/4ffA4vjA4/jB4/jD5PjG5fnI5vnJ5vnO6frQ6vrR6vrS6vrU7PvY7frY7fvY7fzZ7vva7vvb7vrc7/vf8Pvg8fvg8fzh8fvi8vzj8vzk8/zl8/zq9fzs9vzs9v3t9/3v+P7w+P3x+P3x+f7y+f3y+f7z+f71+v71+/72+/74+/74/P75/P75/P/6/P77/f/8/f79/v79/v/+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiwCTJGkRIokFC0mKGBEo0EYAgwh3IBEIQ0cSBAsOBvmR5AiREQMSJAEQoYLFGi6ACHwgQAGDEzlU3BDo4cMHDQ4EyqiBo6eHnxskCEwxoycOgRgIXOhAYgQFFgJXFJiQxIAIEw2SoMhgI0YPgxxUqCgBIskQHgJ9HEgiNgkEIQyT0HjBVkWSGTkEBgQAIfkECQQASAAsAAAAAAwADACHS63rWbTtXbXtabvuf8XxicnykM3ymdH0ntP0qNf1qdf1rNn2r9r2sNv3tN33t973ud/3ut/3vOD4wuP4w+P3w+T4xOT5xeX5yOb4yeb5yef5zOj50Or60ur60+v61ez61uz62e362+372+783O783O/73e/73vD64PH84fH74/L85PP85fP85vT86PX96vb96/b97vf97/j+8Pj98fn+8vn98vn+8vr+8/r+9Pr+9fr+9fv+9vr+9vv99vv++fz++v3++/3//P3+/P3//P7//v7+/v7//v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAkSBR8QHJhAlIjBQRKJBGAIMIfzBsUQMJggUHhQxBcoRIiAEJkAB4MEEijhdABDoQoIDBiR4udgjs4MEDhgYCZ9zAwbODzwwSBKqQwROHQAsEKHAYQeLCCoEpCkRAYkCECQdIUGiwAUMHkgobVKgoAQJJEB8CeRwYqAIJBIkMY7BgiyRGDoEBAQAh+QQJAwBCACwAAAAADAAMAIdSsOxgt+5kue5wv/CHyfKQzfOY0fSg1PWi1fWs2fat2vav2vay3Paz3Pa33ve53va64Pi+4fi/4fi/4vjE5PjG5PjH5fjH5fnL5vnM5/nM6PnP6fnQ6vrT6vrU6/rV7PrX7fva7vvb7/vd7/ve7/zf7/vf8Pvg8fzh8fvj8vzk8vzk8/zl8/zn9Pzo9f3s9v3u9/3v9/3v+P3w+f7x+P3z+f3z+f70+f71+v71+/72+/73+/74/P/6/f76/f/7/f79/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IgwCFCFEBQggFCgITCqQRwCBChS1sCEGw4GDCIEBEDEggBMCDhzpm/BDoQIACBih6wOAh0MOHDxgaCLxxA4dNDzgzSBDYgoZNHAIvEKjQgUQJDS4EpigQQYiBEScgCFnBocYLHUIsbGDBwkQIIT92CNxxQAhXIRN8KJTRwiwLITFyCAwIACH5BAkDAEkALAAAAAAMAAwAhzel6Uar61m07Wa672u873bB8I3L85PO85bQ9J7T9KLV9KXW9abX9avY9bDb9rDc97Lc9rTc9rbe97ne9rvg97vg+L7h98Hj+MLj+MLj+cbl+Mbl+crm+Mrn+cvn+czn+M/p+tDp+dLq+tPr+9br+tbs+tft+tft+9jt+t3w/N7w/ODw/ODx/OLx++Lx/OPy/OXz/Of0/Oj0/On1/er1/Ov2/e32/e/3/fD4/fH5/vL5/vP5/fT5/vX6/vb7/vf7/vj7/vj8/vj8//r8/vr9/vv9//z9//3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkgYEiiQYNSUKwEChQxwCDCAPcEChjR5IFEA4qOCAQSYoCDpIIoDABQBIiPo4IrEDgQYQGFnwUEXjChIkPEgQG+cHzx4mfIDAIpMGjp8AOBjiQWOFiRA2BMBBkSJKARYsLSWKU6GHDRxIPImLEeKEiiREgAoUwyBojyYYhDJPgmME2SQ6vSQICACH5BAkEAEIALAAAAAAMAAwAhz2n6kyu62C37my873G/73zE8JXP9JbP853T9aXW9abW9qnY9a3a9q7b9bPd9rbe97jf97nf973h+L7i+L/j+MLj+Mbk+cbl+cjm+cnn+czn+c3o+c7p+s/p+tLq+tLr+tbs+9nu+9ru+93v+97w++Hx++Hx/OLx/OPy/OXz/ebz/Ob0/en1/On1/er1/Ov2/e72/O73/e/4/vD4/vH4/fL5/fP6/vT6/vb6/ff7/vj7/vn8/vr9//v8/vv9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIUIUSFCSIYMQj6YECjQxgCDCAPMEMjihpAFDw4mOMCQRAEHQgRQkABASBAgDCcQcAChQQUgQQSGmNkhgsAeO3LumBnCgwWBMHDoFMjBwAYRKAjGEKgCwQUhCk6kwCDkxYgcMnII6QCiRYsVJYT84CFQBwMhXoVo8MFQCA0XaFsIqaFVSEAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zlM3ymtH0m9LzodT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t973ueD3uuD3vOD3v+H3weL4weP4yef5y+f5z+n60Or60er60ev60ur60+v61Ov61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j97/j+8Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIwAnTiRkcJJhw5OSrgQKHBIAYMIB/gQeKOIEwgWDjpQ4ITHihYHKjghoCGDACcIAnwQuMEAhQsSEgBgIBDFiRMiMAiMkEOJTxRASXAQCASJTyUCQSwIoWIGDhZBBNJoMPRBjBoenPR4ceSHESciTOjQYQOGkyZLBCaZ4GSskxFMGDoRsqOtDidEjggMCAAh+QQJAwBJACwAAAAADAAMAIc6pulJretLretZtO1uvu55wvB/xfGJyfKVz/OXz/Oe0/Si1fSk1vWq2fas2fax3Pay3Paz3Pa03fe53va53/e74Pi84fe94ffA4vjB4/jE5PjE5PnM5/jN6PnR6vrU6vrU6/rU6/vV7PrW7PrX7frZ7vrc7/vd7/vd8Pvf8Pzg8fvh8fvj8vzn9Pzo9f3p9fzp9f3q9fzq9v3r9v3s9v3t9vzt9/3u9/3u+P3v9/3x+f7z+v70+v71+v31+v71+/72+/74/P75/P76/f78/f78/v78/v/9/v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IjACTJIFxIkmHDklEsBAokEcBgwgH6BA4w0eSBxYOOlCQJIeKFQcqJCGgIYOAJAgCeBC4wcCECxESAGAgEMWJEx8wCIRQ44hPFEBJcBDYo4jPIwJBLAiRQgYOFz8EymiAUEKLGCOS7JAxREeQJCNM2LBB40USJEYECqGQZGySEkQYJuFxo62NJECECAwIACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9JvR86LV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg97/i+MDi98Pj+MTk+Mbk+cfl+c/p+tDq+dHq+tPr+tfs+tft+9jt+9ns+tru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiGAIsUWUGiiAYNRT6oECgwRwGDCAfcEOhiR5EHFA42UFCExokUBygUIYDBgoAiCAJ0EJjBwIQKERIAWCCQhAkTIC4IhECDIYmfITYI/EGEoUAPDDygeHEjhg+BLBxwKCKhhYwRRXbYEIKjRxERJGqIhVGEyBCBQUSKLVLiLEMdM4qs5QFEYEAAIfkECQMAQQAsAAAAAAwADACHSK3rVrPsWbTtZrrvfMPwhsjxjcvzltD0nNL0ntP0odT1pdb1qtj1sNv2stz2tt32t973uN73ud/3weP4wuP4w+P4xuX4xuX5yOX5yuf50er60+r61Ov61ez62O362u772+762+772+/73fD83vD84fH74fH84vH74vL84/L85PP85fL85fP85vT86/b97fb97ff98Pf98Pj98fn+8vn+8/n+8/r+9fr+9vv++fz++vz++v3++/3++/3//f7+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAgwRxYSKIBg1BPLAQKPBGAYMIB9AQ+AJHkAgUDjpYEGTGCRYHKAQhgOGCgCAIAnAQmMHAhAoSEgBgILAEChQfLAhUAIGCzxJAQWwQOGKC0QkCRTQIsSLGDRw9BMJ40CHIhBcyVATZgeNHjRxBSKSgQcOGDIFABOq4EIRskBY+GAbBMaPtxBw8BAYEACH5BAkDAEIALAAAAAAMAAwAh0+w61227WC37my874PH8ozL8pXP9J3T9aDU9KLV9aXV9anY9a7b9rbe97ff97ne97zg97zh97zh+MPj+MPk+MTk+cbl+Mbl+cjm+cnm+crm+czn+c7p+tPr+tbr+dbs+tjt+tru+9zv+97v+97w+9/x/ODw/OHx++Ly/OTz/Obz/Ob0/en1/ev2/Oz2/e33/e73/e/4/vD4/vH4/fL5/fP5/vP6/vT6/fT6/vX6/vb7/vf7/vn8/vr9//v9//z9/vz9//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIUIcYFCSIcOQkKoECgwRwGDCAfYEBhjhxAJFw42WCBkRgoVBy4IIaAhgwAhCAJ8EMjBwAQLERIAYCAwhU0RGgQqeFChp80UJTwINEGhKAWBJByMYIGDB5AgAmFAACEEg4waLYQEASIERw8hJ1bgwKHjBkOBPjZ0xSHkBVSGO2isFeLjh8CAACH5BAkEAEwALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pHN85PO85vS85zS9KLV9aPW9aTW9aXW9ajY9a3a9rHc97je9rng97zg+L7h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+crn+cvn+szo+c7p+c7p+s/p+tDq+tHq+tPr+tbt+9jt+9rt+tzv+97w+9/w++Hx++Hx/OLy/OTz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiNAJkwuQGDyYkTTFTQEChQCAKDCAv0ELhjCJMLHQ5OgMCER4waDDwwMSDiAwEmDQagEFgiwQYOFhwIiCBwhgwZK0IIfEBBg88ZQF2kEKhAQoajAltUeIFjCAgACwTqwKCCyQgfQHgwORCARJAjTGLYECLECBEmOVgITGKCCVkmPZYwZFLkh1shTJAoERgQACH5BAkDAEsALAAAAAAMAAwAhzqm6Umt61217Wm77m6+7nnC8JDN8pXP85nR9J/U9aLV9KXW9ajX9ajY9qrZ9qvZ9rHc9rTd97re97zh977h98Hi+MPk+MXl+cfl+cjm+cnn+cro+cvo+czo+c7o+s7p+s/p+dDo+tHp+dHq+tTr+tbs+tjt+9nt+tnu+t3v+97w/ODx++Dx/OHx++Ty/eTz/OXz/Ob0/Ob0/ej0/Oj0/en1/On1/er2/ez2/e73/e/3/fD5/vH5/vL5/fL5/vT6/vX6/fb6/vb7/vj8/vn8/vr9/vv9//z9/vz9//7+/v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJcsyQFjiQkTS1LYECgwCAKDCAv8EMhjyBILHQ5OgLCkR4wbDj4sMRDCA4ElDQacEEhCwQYOFRgIiCCQxowZLUQIfEAhg08aQF2oEJhAAoajAl9ckLGjCAgACwT60MBiSQkgQ4gsORBghBAjS2rgGDLkCJIlOlYIPIJiCdklWhnCFeLWopIkAgMCACH5BAkDAEsALAAAAAAMAAwAhy+h6D+o6kGp6VCw7GS57nC/8HXA8H/F8I/M85jR9JnR9J7T9J/U9aDU9aLU9ajY9anY9avZ9qzY9q7Z9bDb9rTd9rfe973h+L7h97/i+MDi+MTj+Mfl+Mrn+czo+c3o+M7o+c/p+c/p+tDp+tDq+tHq+tPq+tPr+tXs+tfs+tru+9vv+93v+9/w+9/x/ODx++Hx++Lz/OPx/OTz/Obz/Of0/Oj1/en0/Or1/er2/ev2/O33/e/4/e/4/vD4/fD4/vL5/vP5/fP5/vT6/vf7/vj7/vj8/vr8/vr9/vv9/v3+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJcs4VFjiQoVS1rgECiQSAODCA8MEQikyBIOIQ5mqLBESA0dFEosSWBihIElEQqsEJgCwgcQGyQQsCAQh00ZKARO0NChp00cNGIIdIChZweBNjzcEHJhgYAHAoOQmLGEhZEcAJYoGHCCSJIlO34gQcIAwRIfMAQqebFk7JIAPRguOUKkLZIlIlwIDAgAIfkECQQATAAsAAAAAAwADACHN6XpRqvrSK3rVrPsa7zvdsHwfMPwhsjxk87znNL0ntP0oNT0otX0pdb1ptf1q9n2r9v2sNv2sdv2tt32uN73u+D4wOL4wOP5wuP3wuP4x+X5y+f5zOj5zOj60On50en50er50ur60+r60+v71Ov61ez61ez71uz62e372+/73O/73fD84PH84fH84vH75PP85fP85vP85vT85/T86PT86fT96fX96/b97PX87Pb97fb97ff97/f98Pj98fn+8/n98/n+8/r+9fr+9vr++Pv++Pz/+fz++vz9+/3+/P3+/P3//f7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIkAmTDpYYOJChVMWtwQKLCIA4MIDwgRCMQIkw0hDmagwOQHjR0TSjBRYEKEASYQCqwQmCICiA8aIhCoIDCHzRgoBErAwKGnzRw1YAhscKGDUYE3RugYYmGBgAcChZyYweTFERwAmCQYQIKIkoFBkiRhgICJDxcCl8hgIpZJAB4MmSCx2NYDC4EBAQAh+QQJAwBFACwAAAAADAAMAIc9p+pMrutPsOtdtu1xv+98xPCDx/KMy/KWz/Og1PSj1fSl1vWm1vao1/Wt2vau2vaz3faz3fe03Pa33/e84Pe84fi+4vjC4/jD5PjG5fnL6PrO6frP6frS6/rU6/rV6/rV7PvW7PrW7PvX7PrZ7vva7vvb7vrd7/ve8Pvh8fzi8vzk8/zp9Pzp9fzp9f3q9fzr9fzr9vzr9v3s9v3t9/3u9/3v9/7w+P7x+P30+v30+v71+v72+/73+/74+/75/P76/f/7/f/8/f79/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IiQCLFMHxoggKFEVUzBAo0IcDgwgP7BCoA0gRDiIOZqhQREeLGhRIFGEw4oOBIhEKIDQ4wQMIDRAIWBBYo6YLEwIlZODAs2YNGCwENriwoSjNEjh+YFAg4IHAHidkFIkxxAaAIgkGhAAipEgOHkSILEAwcIVAIjSKhC0S4AbDIkKCqCVSpEMKgQEBACH5BAkDAEkALAAAAAAMAAwAh0Wr61Ox7Faz7WO47nnD8YPH8YrK8pPO85rR9KTW9afW9anY9qzY9azZ9qza9rHb9rPd97Tc9rfe9rff977h97/h98Di+MHj+MPk+MXl+cjm+cnm+c7p+tDq+tHq+tLq+tTs+9jt+tjt+9jt/Nnu+9ru+9vu+tzv+9/w++Dx++Dx/OHx++Ly/OPy/OTz/OXz/Or1/Oz2/Oz2/e33/e/4/vD4/fH4/fH5/vL5/fL5/vP5/vT6/fX6/vX7/vb7/vj7/vj8/vn8/vn8//r8/vv9//z9/v3+/v3+//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJMkwSEjSYoUSVzMEChQCASDCA/4EMhjSJIPJA5usJCkB4waGE4kaVAihIEkEwqoELiCgogRHCYQuCDwhk0ZKARK0OChp80bNGIIdJChg1GBNlLsMMFAgYAHAoG0oJEkR4UIAJIkGCCCyJEkP4JYsLAAQdUXApHoSDI2SYAaDJMYKcKWIwgWAgMCACH5BAkEAEkALAAAAAAMAAwAh0ut61m07V217Wm77n/F8YnJ8pDN8pnR9J7T9KjY9qnX9azZ9q7a9bDb97Td97Xd97fe97nf97rf97vg97zg+MLj+MPk+MTk+cXl+cfl+Mnn+crn+czo+dDq+tLq+tPr+tXs+tbs+tnt+tvt+9vu/Nzu/Nzv+93v+97w+uDx/OHx++Py/OTz/OXz/Ob0/Oj1/er2/ev2/e73/e/4/vD4/fH5/vL5/fL5/vL6/vP6/vT6/vX6/vX7/vb6/vb7/vj8/fn8/vr9/vv9//z9/vz9//z+//7+/v7+//7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiJAJMk0SEjyYoVSVoUFJgESASDCA/0EOhDSJIQJg5ysJBkR4wbGlIkcXBihIEkEgqoEMgCQwkSHSYQuCAwh80ZCJNQ2PChp80cOGgIbJDBg1GBPF78QMFAgYAHAoPAyNGwAgQASRIMEFEESRIiQypUWIAgiQ0XDIEkEZskQA2GSYwcWVshCYicAQEAIfkECQMAQQAsAAAAAAwADACHUrDsYLfuZLnucL/wh8nykM3zmNH0oNT1otX1q9n2rdr2r9r2stv1s9z2uN/3ud72uuD4vuH3vuH4v+H4v+L4xOT4x+X4x+X5yuX5zOj5zej5z+n50Or60+r61Ov61ez61+372u772+/73e/73u/83+/73/D74PH84fH74/L85PL85PP85fP85/T86PX97Pb97vf97/f97/j98Pn+8fj98/n98/n+9Pn+9fr+9fv+9vv+9/v++Pz/+v3/+/3+/f7//v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIMAgwTJESMICxZBWsgQKLAHBYMID+wQuMNHkBAmDm6wEETHixocVgSBcGKEgSASCqQQ6CJDCRIdIhC4IBCHTRotBE7Q8KGnTRw3bghsgMGDUYE8YPhAwUCBAAcCfczQIbDCAwBBEgwQ8QMIwwoVFiAIYiMnwyBggwSgcfZrhSAgVAgMCAAh+QQJAwBJACwAAAAADAAMAIc3pelGq+tZtO1muu9rvO92wfCNy/OTzvOW0PSe0/Si1fSl1vWm1/Wr2PWv2/aw3Pey3Pa03Pa23ve53va74Pe84Pe/4vjB4/jC4/fC4/jC4/nG5fjG5fnK5/nL5/nM5/nP6fnQ6fnS6vrT6/vW6/rW7PrX7frX7fvY7frd8Pze8Pzg8Pzg8fzi8fvi8fzj8vzl8/zn9Pzo9Pzp9f3q9fzr9v3t9v3v9/3w+P3x+f7y+f7z+f30+f71+v72+/73+/74+/74/P74/P/6/P76/f77/f/8/f/9/v/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhwCTJPGRI0mMGElm4BAocAgHgwgZCBEIxEgSFS8OivAw0EaPEggvtGCRIIkGBDAE1hjhYgUJDAY6CPxBkwcNgRlAmNhJk2YQgRI+nBgqsIgPCw0iPCBAQeARH0SSAJhQQUASBwVSIBF4QMGGDRAWJNkhQ+CNAEm+Jhmgg2ESFiHSbkiCImWSgAAh+QQJBABDACwAAAAADAAMAIc9p+pMrutgt+5svO9xv+98xPCVz/SWz/Od0/Wl1vWm1vap2PWt2vau2/Wz3faz3fe23ve43/e53/e94fi+4vi/4/jD5PjG5PnG5fjG5fnI5vnJ5/nM5/nO6frP6frS6vrS6/rW7PvZ7vva7vvd7/ve8Pvh8fvh8fzi8fzj8vzl8/3m8/zm9P3p9fzp9f3q9fzr9fzu9vzu9/3v+P7w+P7x+P3y+f3z+v70+v72+v33+/74+/75/P76/f/7/P77/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhQCHDNFhY4gLF0Ne1BAo8AcHgwgZ7BDYA8gQEywOhvAwcIYOEjCGaFCBQsGQDAhWCJQxYkWKERgMdBDIo2aOGAIvfBDBs2ZNHwIleOApQqCQIBYaRHBAgALDIEKGAJhQQcCQBwVKMDyQYMMGCAuG4GghkEaAIV6HDLjBcMgJEGg3DGkpMCAAIfkECQMATgAsAAAAAAwADACHM6LpQ6rrRavrU7HsZ7vuc8DwecPxg8fxkc3zmtH0m9LzoNT0odT1o9b1qdj2rNn2rdr2rtr1sdr1s933tt73t9/3ueD3uuD3vOD3v+H3weL4wuT5yef5yuf5y+f5z+n60Or60er60ur60uv60+v61Or61Oz72e772+772+/73O/73e/83/D74PH74PH84vL84/L85fP85fP95/T85/T96PX86PX96fX96vX86vb96/b86/b97Pb97/j98Pj98Pj+8fj88fj98vn98/n+9Pr+9fv+9/v++Pz++fz++fz/+/3++/3//P7//f7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAnTg5QsTJjh1OeAgRKJAJCYMIJyQRuKSJkxg3Dp4Q4cTIjyMwejj5YEPGAyccGtQQGKRFDhorOigIIVCJTSRABHIogaKnTSU6IgjEMCKFUYEMACyQcIGCgQ0CQQRA4ERABg0EnFQ44IKFyAQOPHiwAMFJERwCfQxwItZJgSEMnbwwwdaDExUzBAYEACH5BAkDAEgALAAAAAAMAAwAhzqm6Umt60ut61m07W6+7nnC8H/F8YnJ8pXP857T9KLV9KPU9aTW9arZ9qzZ9rHc9rLc9rPc9rTd97ne9rnf97rf97zh973h98Di+MHj+MTk+MXl+czn+M3o+c7o+tHq+tTr+tXs+tbs+tfs+tnu+tzv+93v+93w+9/w/ODx++Hx++Py/Of0/Oj1/en1/On1/er1/Or2/ev2/ez2/e32/O33/e73/e74/e/3/fH5/vP6/vT6/vX6/fX6/vX7/vb7/vj8/vn8/vr9/vz9/vz+/vz+//3+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiKAJEgCfIDSY0aSGzsEChwCAmDCCkEEVjkCBIXMw6WEIEESA4hMXQgEQGDhQQkHRrEEOijxY0YKDwoACHQiE0iPARyGGGip00jNCAIxADihFGBDAAsiHBhgoENAj8EQIBEQAYNBJBUOKAiBQ4kCRx06GDhAZIeMgTmGICyA5ICCxmuCNEWiYkXAgMCACH5BAkEAEUALAAAAAAMAAwAh0Gp6VCw7FKw7GC37nXA8H/F8IfJ8pDN85nR9KLV9afX9anY9a/a9rDb9rTd9rbe97fe9rrg+Lzg977h+L/i+MDh98Pj+MTk+Mbl+cjm+c/p+tDq+dHq+tLq+tPr+tfs+tft+9nt+9ru+93v+9/w++Dx++Dx/OHx++Lx/OPy/OTy/Or1/ev2/Ov2/uz2/e32/e33/e73/e73/u/3/fD4/fD4/vD5/vH4/fL5/vT6/vX7/vb7/vf7/vj7/vj8//n8//r8/vr9//v9/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiHAIsUAcKjSI0aRWboEChwSAmDCCkEaUikCIyDNUiIKNIDhxAbO4qMkNEiQhEODVgI9BHjxgsUHRZ8YCiQyA+BG0KY2MmQxgOBFz6QGCpQAQAFECpIMJBBoIcACIoIsICBQJEJB1KcoFEkAQMNGig4KLLDhcAbA4qALVIgB00VINRqKEJihcCAACH5BAkDAEIALAAAAAAMAAwAh0it61az7Fm07Wa673zD8IbI8Y3L85bQ9JzS9KHU9aXW9anY9qrY9bDb9rLc9rbd9rbe97je97nf98Hj+MLj+MLj+cPj+Mbl+Mbl+cjm+cvn+dHq+tPq+tTr+tXr+tXs+tjt+tnt+tvv+9zv+93w/N7w/OHx++Hx/OLx++Ly/OPy/OTz/OXy/OXz/Ob0/Ov2/e32/e33/fD3/fD4/fH5/vL5/vP5/vP6/vX6/vb7/vn8/vr8/vr9/vv9/vv9//3+/v3+//7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiLAIUI6aFDSI0aQmjkECjwhwuDCDHsEBhE4IwbB1WUEKLDBpAcPISsmAFjgpAPD2II9JEDhwwWHhqIEDiBgk0SAjmMSMFzgk8ICQReCGGiqEAGABZIsDDBgAaBHQIgECIAQwYCQiocaIGChhAFDjZsoBBBSA4YAmsMECJWSAEcDIW0AMF2g5ATLwQGBAAh+QQJAwBDACwAAAAADAAMAIdPsOtdtu1gt+5svO+Dx/KMy/KVz/Sd0/Wg1PSl1fWp2PWt2fWu2/a23ve33/e43va84Pe84fe84fjD4/jD5PjE5PnG5fjG5fnI5vnJ5vnK5vnK5/nM5/nO6fnT6/rW6/nW7PrY7frZ7fva7vvc7/ve8Pvf8fzg8Pzh8fvi8vzk8/zm8/zm9P3p9f3r9vzs9v3t9/3u9/3v+P7w+P7x+P3y+f3z+f7z+v70+v30+v71+v72+/73+/75/P76/f/7/f/8/f78/f/+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8IhgCHDAHyY0iOHENq8BAoUAgMgwg5FGQ4BMeOgyxQDPGBMIiQIS5szMAwJASEGA2D9MjRQoSDEgIpVJh5QuAHEypyUtj5IIFADSRyqhDIAMCCCBYmGOggEEQABEMEZNhAYMiFAytU0BiioIEHDxckDOEhQ+CNAUO+Dimgg+KKEWk9DEnxQmBAACH5BAkEAEoALAAAAAAMAAwAhzOi6UOq61az7WO47me77nPA8IrK8pLN85PO85vS85zS9KHU9aPW9aTW9ajY9a3a9rDb9rHc97nf97ng97vf977h97/i98Di+MPk+MXk+Mbl+cfm+Mnm+Mnm+cnn+cvn+szo+c7p+c7p+s/p+tDq+tHq+dPr+tbt+9jt+9rt+tzv+97w/N/w++Hx++Tz/OXz/Ob0/Ob0/ef0/Oj1/On1/e33/e33/u/4/fD4/fD4/vL5/vP5/vP6/vT6/vX6/fX6/vb7/vf7/vj7/vj8/vn8/vr8/vz9/vz+//3+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wiMAJUoQWJECRAgSnoMESgwyQ6DCE0cEcjihhIhRA7SeKGkyA8SAQ4o0eGDxwglKjDgELgAAIggNlZUaCEwgwYNEhQITNEChs8MQCk4EBhiRYyjAiMIgGCBw4YEJQSiGNBACYEPIgwo8cBgxgsdSh5MOHGiwwUlQXII3FFACVklCBAylKHC7QklLmoIDAgAIfkECQMASwAsAAAAAAwADACHOqbpSa3rXbXtabvubr7uecLwkM3yltD0mdH0n9T1otX0pNb1qNj2qtn2q9n2sdz2stv1tN33u9/3vOH3veD3weL4w+T4xeX5x+X5yOb5yef5yuj5y+j5zOj5zej5zuj6z+n50Oj60en50er61ez61uz62O372e362e763e/73vD84PH74PH84fH84fL85PL85PP85fP85vT86PT86PT96fX86fX96vb97Pb97vf97/f98Pn+8fn+8vn98vn+9Pr+9fr99vr+9vv++Pz++fz++v3++/3//P3+/P3//v7+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////CIsAlyxJomTJkCFLhBARyHDhwSUojghcoWMJkiMHcdRYYkTIiAAHlhAZAqTEEhYafAhcAABEkR0uLsAQiCFDBgkJBKp4MaMnhp8UHAgU0YKGUYERBECowGGDAhICTwxgsITAhxAGlnhocENGjyUPJpgw0cGCQR4CfxRYMnYJgiAMl9hIwdbEkhg5BAYEADsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='></span></em></strong><br>"""
            # self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

            message = get_agent_reply_msg_title_formatted(self.tr(agent_name))
            add_msg_to_message_window(self.messageBrowser.page(), message, 1)

            owner = f'{self.tr(agent_name)}'

            self.messages.append({"role": "user", "content": task_content_to_run})
            messages = self.messages  # 分开两行否则加不进去

            messages = [{"role": "user", "content": task_content_to_run}]  # 仅仅单纯执行这一次任务，忽略上面的历史

            self.thread = AgentWorkerThread(self, agent, task_id_to_run, task_content_to_run, self.agent_multi_cfg, self.task_id, self.is_first, messages, owner, self.messageBrowser.page())
            self.thread.finished.connect(self.showTaskResult)
            self.thread.start()

        else:
            print("任务全部完成")

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
        application.open_multi_agent_task_chat(self.agent_multi_cfg)

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
                             "Markdown Files (*.md)")
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "QFileDialog.getOpenFileNames()", openFilesPath,
                                                filter_extensions, options=options)

        self.add_attachment_area(files)

    def opendialogpluginbak(self):
        pluginselectedList = self.pluginselectedList
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All(is_delete=0)
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
                    create_item(agent.detail),
                    create_item(agent.version),
                    create_item(agent.description),
                    create_item("操作")
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)

                selected_items.append(row_data)

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.plugin_id),
                create_item(agent.name),
                create_item(agent.alias_name),
                create_item(agent.detail),
                create_item(agent.version),
                create_item(agent.description),
                create_item("操作")
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

            # Create a combo box for '模型型号'
            combo_item = QStandardItem("gpt-3.5-turbo")
            model.setItem(row, 4, combo_item)

            # Placeholder for button, actual button will be inserted by delegate
            model.setItem(row, 7, QStandardItem())

            row += 1

        dialog = PluginFreezeTableDialog(model)

        items_per_row = {
            0: ["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
            1: ["gpt-3.5-turbo22", "gpt-422", "gpt-4o22"],
            2: ["gpt-3.5-turbo23", "gpt-43", "gpt-4o3"],
            3: ["gpt-3.5-turbo4", "gpt-444", "gpt-444"],
            4: ["gpt-3.5-55", "gpt-55", "gpt-55"],
            # Add more rows as needed
        }
        combo_delegate = ComboBoxDelegate(items_per_row, dialog.tableView)
        dialog.tableView.setItemDelegateForColumn(4, combo_delegate)
        button_delegate = ButtonDelegate(dialog.tableView)
        dialog.tableView.setItemDelegateForColumn(7, button_delegate)

        if dialog.exec_() == QDialog.Accepted:
            self.pluginselectedList = dialog.getResult()
            print("self.pluginselectedList:", self.pluginselectedList)
            print("self.pluginselectedListjoin:", ",".join(self.pluginselectedList))
            update_AgentCfg(self.agent_cfg.id, plugins=",".join(self.pluginselectedList))
            self.agent.reset_cfg_plugin_llm()
            tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            tech_list.reload()

    def opendialogplugin(self):
        pluginselectedList = self.pluginselectedList
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All(is_delete=0)
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
            # update_AgentCfg(self.agent_cfg.id, plugins=",".join(self.pluginselectedList))
            # self.agent.reset_cfg_plugin_llm()
            # tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            # tech_list.reload()
            # self.set_messagebox_placeholder()

    def opendialogkm(self):
        kmselectedList = self.kmselectedList
        print(kmselectedList)
        selected_items = []
        unselected_items = []

        agents = query_KMCfg_All(is_delete=0)
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
            # update_AgentCfg(self.agent_cfg.id, kms=",".join(self.kmselectedList))
            # self.agent.reload_agent_cfg()
            # tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            # tech_list.reload()

    def openLink(self, url):
        webbrowser.open(url.toString())

    def generate_image(self, prompt, model="dall-e-3", n=1, size="1024x1024"):
        # ***dall-e-3的n必须是1
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
            self.messageEdit.setPlaceholderText("Powered by " + modelname)

    def save_task_output(self, output):
        print("cjrok the task output:", output)
        topic = self.task_command
        content = output
        attachment_content_list = json.dumps(self.attachment_content_list, ensure_ascii=False)  # km部分已经在agent中进行了处理，添加进去了

        self.owner="agent001"#cjr edit
        add_AgentTaskMulti(self.task_id, topic, content, self.owner, self.agent_multi_cfg.group_id, self.is_first)


        # self.modelname="gpt4-ooo"
        # record_id = add_AgentTask(self.task_id, question, question, answer, self.modelname, self.agent_cfg.user_id, self.is_first, attachment_content_list)
        # self.onTaskFinished(question, answer, record_id)
