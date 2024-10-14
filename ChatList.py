import json
import os

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox, QInputDialog, QTreeWidgetItemIterator
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from db.DBFactory import query_AIChat_Content,query_AIChatMessages_All,query_AgentTask, query_AgentTask_Search_Content, query_AgentTask_Content, query_AgentTask_Search_First, AgentTask, deleteTasksFromDatabase, update_AgentTask

from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, get_content_from_attachment_content_list, add_attachment_to_message_window


class ChatList(QTreeWidget):
    """ChatList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)

    def __init__(self, parent, agent):

        super(ChatList, self).__init__(parent)
        print("ChatList parent", parent)
        self.jid = parent.jid
        self.connection = None
        self.parent = parent
        self.agent = agent
        self.agent_cfg = self.agent
        self.current_conversation_id = ""
        self.tasks_history = None
        self.browser_page = None
        self.is_browser_page_loaded = False

        self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
        # self.setSortingEnabled(True)#排序
        # self.sortItems(0, Qt.AscendingOrder)#排序
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
        self.rename_action.triggered.connect(self.rename)
        self.menu.addAction(self.rename_action)

        self.delete_action = QAction(QIcon("images/delete.png"), "删除", self)
        self.delete_action.triggered.connect(self.delete_item)
        self.menu.addAction(self.delete_action)

        # self.menu.addAction(QIcon("images/infos.png"), "信息", self.delete_item)

        self.customContextMenuRequested.connect(self.context)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        self.chat_list = query_AIChatMessages_All(is_first=True, owner_account=self.agent.account,friend_account=self.jid)
        for record in self.chat_list:
            self.addItem(record.title.replace("\n", ""), record.id)
            # print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            item = self.currentItem()
            if item:
                reply = QMessageBox.question(self, '删除确定',
                                             f"您确定要删除 '{item.text(0)}'?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    column = 0
                    id_value = item.data(column, Qt.UserRole)
                    # 从数据库中删除所有conversation_id相同的记录
                    deleteTasksFromDatabase(id_value)

                    index = self.indexOfTopLevelItem(item)
                    if index != -1:
                        self.takeTopLevelItem(index)
                    else:
                        parent = item.parent()
                        parent.removeChild(item)
        else:
            super(ChatList, self).keyPressEvent(event)

    def scrollContentsBy(self, dx, dy):
        # 调用父类方法处理滚动
        super().scrollContentsBy(dx, dy)

        # 判断是否滚动到底部
        if self.verticalScrollBar().value() == self.verticalScrollBar().maximum():
            print("Reached bottom!")

    def addItem(self, name, id, is_top=False):
        item_count = self.topLevelItemCount()

        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "所有")
        else:
            group_item = self.topLevelItem(0)
        # print("adding item:",name)

        # top_item = QTreeWidgetItem(group_item)#不要这样构造，这样排序会缺省按字符排序，排序乱了
        top_item = QTreeWidgetItem()
        top_item.setText(0, name[0:50])
        top_item.setToolTip(0, name)
        top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
        if is_top == False:
            # print("not top")
            group_item.addChild(top_item)
        else:
            print("im toppppppppp....")
            group_item.insertChild(0, top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()

    def context(self, pos):
        item = self.itemAt(pos)

        self.current_Item = item
        self.menu.popup(self.mapToGlobal(pos))

    def deselect_all_items(self):
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            iterator.value().setSelected(False)
            iterator += 1

    def rename(self):
        self.rename_signal.emit(self.currentItem)
        item = self.current_Item

        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:

            oldName = item.text(0)
            newName, ok = QInputDialog.getText(self, "重命名", "新名称:", text=oldName)
            if ok and newName:
                item.setText(0, newName)
                column = 0
                id_value = item.data(column, Qt.UserRole)
                update_AgentTask(id_value, title=newName)
        else:
            QMessageBox.critical(None, "警告", "分类名不能重命名", QMessageBox.Ok)

    def search(self, key_word):
        print("chat_list searching", key_word)
        self.reload(key_word)


    def reload(self, key_word):
        self.clear()

        self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
        self.rename_action.triggered.connect(self.rename)
        self.menu.addAction(self.rename_action)

        self.delete_action = QAction(QIcon("images/infos.png"), "删除", self)
        self.delete_action.triggered.connect(self.delete_item)
        self.menu.addAction(self.delete_action)

        self.customContextMenuRequested.connect(self.context)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        if key_word.startswith('+++'):
            # 获取上一次的搜索结果并过滤
            filtered_chat_list = [
                record for record in self.chat_list
                if key_word[3:] in record.title or key_word[3:] in record.problem or key_word[3:] in record.answer
            ]
        else:
            self.chat_list = query_AgentTask_Search_Content(
                agent_id=self.agent_cfg.user_id, title=key_word, problem=key_word, answer=key_word
            )
            filtered_chat_list = self.chat_list

        # 创建一个集合来存储已经处理过的 first_record 记录
        processed_first_records = set()

        for record in filtered_chat_list:
            if record.is_first and record.id not in processed_first_records:
                # 处理 first_record
                self.addItem(record.title.replace("\n", ""), record.id)
                processed_first_records.add(record.id)
            elif not record.is_first:
                # 查找是否有相同 conversation_id 且 is_first 为 True 的记录
                first_record = query_AgentTask_Search_First(agent_id=self.agent_cfg.user_id, conversation_id=record.conversation_id)
                if first_record and first_record.id not in processed_first_records:
                    # 处理 first_record
                    self.addItem(first_record.title.replace("\n", ""), first_record.id)
                    processed_first_records.add(first_record.id)

    def delete_item(self):

        item = self.current_Item
        column = 0
        id_value = item.data(column, Qt.UserRole)
        print("id_value", id_value)

        if id_value:

            if item:
                reply = QMessageBox.question(self, '删除确定',
                                             f"您确定要删除 '{item.text(0)}'?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:

                # 从数据库中删除所有conversation_id相同的记录
                deleteTasksFromDatabase(id_value)

                index = self.indexOfTopLevelItem(item)
                if index != -1:
                    self.takeTopLevelItem(index)
                else:
                    parent = item.parent()
                    parent.removeChild(item)
        else:

            QMessageBox.critical(None, "警告", "分类不能删除", QMessageBox.Ok)

    def getInfo(self):
        pass

    def onLoadFinished(self, success):
        if success:
            browser_page = self.browser_page
            records = self.tasks_history
            page_index = 1
            for record in records:
                # self.format_text(browser_page, record.problem, record.answer, record.create_time, record.model_name, page_index)
                self.format_text(browser_page, record, page_index)
                page_index = page_index + 2
            self.is_browser_page_loaded = True
            messagebox = self.messagebox
            messagebox.page_index = page_index - 1

    def on_itemDoubleClicked(self, item, column):
        messagebox = self.parent
        self.messagebox = messagebox
        self.messagebox.new_chat()

        print("双击了：", item.text(column))
        print(column)
        id_value = item.data(column, Qt.UserRole)
        print("双击了：", id_value)
        if id_value == None:
            return (False)

        records = query_AIChat_Content(id=id_value)
        agent = self.agent
        agentcfg = self.agent_cfg


        conversation_id = ""
        if records:
            conversation_id = records[0].conversation_id
            for record in records:
                problem = self.get_record_problem_for_message(record)
                messagebox.messages.append({"role": "user", "content": problem})
                # messagebox.messages.append({"role": "assistant", "content": record.answer})

        messagebox.conversation_id = conversation_id
        messagebox.is_first = False
        browser_page = messagebox.messageBrowser.page()
        browser_page.loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理
        self.browser_page = browser_page
        self.tasks_history = records

        if messagebox.is_browser_page_loaded == True:  # page是否已经load了
            self.is_browser_page_loaded = True

        if self.is_browser_page_loaded == True:
            self.onLoadFinished(True)

        messagebox.messageEdit.setFocus()

    def get_record_problem_for_message(self, record):
        problem = record.content

        return problem

    def format_text(self, browser_page, record, page_index=1, user="用户"):

        question = record.content
        answer = record.content
        create_time = record.create_time
        model_name = record.friend_name

        if record.flag==0:

            message = get_user_ask_msg_title_formatted(page_index, create_time)
            add_msg_to_message_window(browser_page, message, 1)

        # add_msg_to_message_window_and_format(browser_page, question, 2)
            message = get_user_ask_msg_content_formatted(question)
            add_msg_to_message_window(browser_page, message, 2)

        else:

            message = get_agent_reply_msg_title_formatted(model_name, page_index + 1, create_time, False)
            add_msg_to_message_window(browser_page, message, 1)

            if question.startswith("给我画"):
                add_msg_to_message_window(browser_page, answer, 2)
            else:
                add_msg_to_message_window_with_markdown_and_highlight(browser_page, answer, 2)

        directory_path = os.path.join('resource', 'attachment', 'chat', record.conversation_id)
        if record.attachment_list:
            attachments = json.loads(record.attachment_list)
            filtered_attachments = [attachment[2] for attachment in attachments if attachment[0] != "km"]
            if filtered_attachments:
                add_attachment_to_message_window(browser_page, directory_path, filtered_attachments, 2)
