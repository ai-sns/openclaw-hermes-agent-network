import json
import os

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox, QInputDialog, QTreeWidgetItemIterator
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from db.DBFactory import query_AgentTask, query_AgentTask_Search_Content, update_note_mng_by_recordid, query_AgentTask_Search_First, AgentTask, delete_note_mng, update_AgentTask, query_Note_Search_Content
from db.DBFactory import query_note_mng_all,delete_note_mng,query_note_mng
from TaskPage import TaskPage
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, get_content_from_attachment_content_list, add_attachment_to_message_window
from langchainhandler import savevector,delete_vector

class NoteList(QTreeWidget):
    """TaskList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)

    def __init__(self, parent,km_cfg, type_str):

        super(NoteList, self).__init__(parent)
        print("TaskList parent", parent)
        self.connection = None
        self.mainwindow = parent
        self.km_cfg = km_cfg
        self.type_str = type_str
        self.current_task_id = ""
        self.tasks_history = None
        self.browser_page = None
        self.is_browser_page_loaded = False

        self.setHeaderLabel("笔记列表")  # 需要设置此处的值，否则缺省值为1
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

        # self.vector_action = QAction(QIcon("images/vector.png"), "向量化", self)
        # self.vector_action.triggered.connect(self.vector_item)
        # self.menu.addAction(self.vector_action)

        # self.reload_action = QAction(QIcon("images/infos.png"), "刷新", self)
        # self.reload_action.triggered.connect(self.relaod_tree)
        # self.menu.addAction(self.reload_action)

        # self.menu.addAction(QIcon("images/infos.png"), "信息", self.delete_item)

        self.customContextMenuRequested.connect(self.context)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
        if type_str=="recent":
            self.tasklist = query_note_mng_all(10,km_id=km_cfg.km_id)
        else:
            self.tasklist = query_note_mng_all(-1,km_id=km_cfg.km_id)
        for record in self.tasklist:
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
                    # 从数据库中删除所有task_id相同的记录
                    delete_note_mng(id=id_value)

                    index = self.indexOfTopLevelItem(item)
                    if index != -1:
                        self.takeTopLevelItem(index)
                    else:
                        parent = item.parent()
                        parent.removeChild(item)
        else:
            super(NoteList, self).keyPressEvent(event)

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
                update_note_mng_by_recordid(id_value, title=newName)
        else:
            QMessageBox.critical(None, "警告", "分类名不能重命名", QMessageBox.Ok)

    def search(self, key_word):

        self.reload(key_word)
        self.parent().parent().setCurrentIndex(1)

    def relaod_tree(self):
        self.reload()

    def reload(self, key_word=""):
        self.clear()

        self.setHeaderLabel("笔记列表")  # 需要设置此处的值，否则缺省值为1
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

        # self.vector_action = QAction(QIcon("images/vector.png"), "向量化", self)
        # self.vector_action.triggered.connect(self.vector_item)
        # self.menu.addAction(self.vector_action)

        self.customContextMenuRequested.connect(self.context)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        if key_word.startswith('+++'):
            # 获取上一次的搜索结果并过滤
            filtered_tasklist = [
                record for record in self.tasklist
                if key_word[3:] in record.title or key_word[3:] in record.content
            ]
        else:
            self.tasklist = query_Note_Search_Content(
                title=key_word, content=key_word,km_id=self.km_cfg.km_id
            )
            filtered_tasklist = self.tasklist


        for record in filtered_tasklist:
                # 处理 first_record
                self.addItem(record.title.replace("\n", ""), record.id)



    def vector_item(self):

        item = self.current_Item
        column = 0
        id_value = item.data(column, Qt.UserRole)
        print("id_value", id_value)


        note_record =query_note_mng(id=id_value)
        note_id=note_record.note_id

        filepath = os.path.join(os.getcwd(),"km", "note_store", "doc", note_id+".txt")
        persist_directory=os.path.join(os.getcwd(),"km", "note_store", "vector")
        embedding_model_name=""
        savevector(filepath, persist_directory, embedding_model_name)


    def delete_vector(self,note_id):

        filepath = os.path.join(os.getcwd(), "km", self.km_cfg.km_id, "doc", note_id + ".txt")
        persist_directory = os.path.join(os.getcwd(), "km", self.km_cfg.km_id, "vector")

        embedding_model_name = self.km_cfg.embeddingmodel

        if embedding_model_name.lower() == "openai":
            emb_type = "openai"
        else:
            emb_type = "other"

        delete_vector(filepath, persist_directory, embedding_model_name, emb_type)


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

                # 从数据库中删除所有task_id相同的记录
                note_record = query_note_mng(id=id_value)
                note_id = note_record.note_id
                delete_note_mng(id=id_value)
                self.delete_vector(note_id)

                index = self.indexOfTopLevelItem(item)
                if index != -1:
                    self.takeTopLevelItem(index)
                else:
                    parent = item.parent()
                    parent.removeChild(item)
        else:
            QMessageBox.critical(None, "警告", "分类不能删除", QMessageBox.Ok)
            return
        self.parent().parent().findChild(NoteList,"recentnotelist").reload()
        self.parent().parent().findChild(NoteList, "allnotelist").reload()



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
            taskpage = self.taskpage
            taskpage.page_index = page_index - 1

    def on_itemDoubleClicked(self, item, column):
        print("双击了：", item.text(column))
        print(column)
        id_value = item.data(column, Qt.UserRole)
        print("双击了：", id_value)
        if id_value == None:
            return (False)

        self.mainwindow.open_note_editor(self.km_cfg,(id_value))


    def get_record_problem_for_message(self, record):
        attachment_doc_content = ""
        attachment_image_list = []
        retrieve_doc_content = ""
        problem = record.problem
        if record.attachment_list is not None and record.attachment_list != '':
            attachment_content_list = json.loads(record.attachment_list)
            attachment_doc_content, attachment_image_list, retrieve_doc_content = get_content_from_attachment_content_list(attachment_content_list)

        if retrieve_doc_content != "":
            problem = f'请根据后面提供的背景内容回答问题，回答只能限制在背景内容的范围内，问题是：{problem};供参考的背景内容是：{retrieve_doc_content}'


        if attachment_doc_content != "":
            problem = f'{problem};为你提供相关附件内容作为参考，以下是具体的附件内容：{attachment_doc_content}'

        if attachment_image_list:
            # 创建新的列表以包含文本和图像内容
            new_attachment_list = []

            # 添加 question[-1]["content"] 到新列表
            new_attachment_list.append({
                "type": "text",
                "text": problem,
            })

            # 将图像列表的内容添加到新列表中
            new_attachment_list.extend(attachment_image_list)

            problem = new_attachment_list

        return problem

    def format_text(self, browser_page, record, page_index=1, user="用户"):

        question = record.problem
        answer = record.answer
        create_time = record.create_time
        model_name = record.model_name

        message = get_user_ask_msg_title_formatted(page_index, create_time)
        add_msg_to_message_window(browser_page, message, 1)

        # add_msg_to_message_window_and_format(browser_page, question, 2)
        message = get_user_ask_msg_content_formatted(question)
        add_msg_to_message_window(browser_page, message, 2)

        directory_path = os.path.join('resource', 'attachment', 'chat', record.task_id)
        if record.attachment_list:
            attachments = json.loads(record.attachment_list)
            filtered_attachments = [attachment[2] for attachment in attachments if attachment[0] != "km"]
            if filtered_attachments:
                add_attachment_to_message_window(browser_page, directory_path, filtered_attachments, 2)

        message = get_agent_reply_msg_title_formatted(model_name, page_index + 1, create_time, False)
        add_msg_to_message_window(browser_page, message, 1)

        if question.startswith("给我画"):
            add_msg_to_message_window(browser_page, answer, 2)
        else:
            add_msg_to_message_window_with_markdown_and_highlight(browser_page, answer, 2)
