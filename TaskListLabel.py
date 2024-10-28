import json
import os

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox, QInputDialog, \
    QTreeWidgetItemIterator
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal

from TaskList import TaskList
from db.DBFactory import query_AgentTask, query_AgentTask_Search_Content, query_AgentTask_Content, \
    query_AgentTask_Search_First, AgentTask, deleteTasksFromDatabase, update_AgentTask, update_AgentTask_stick, \
    query_AgentTask_ById
from TaskPage import TaskPage
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, \
    get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, \
    add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, \
    get_content_from_attachment_content_list, add_attachment_to_message_window


class TaskListLabel(TaskList):
    def __init__(self, parent, agent):
        # 首先调用父类的初始化方法
        super(TaskListLabel, self).__init__(parent, agent)

    # --> 加载 数据
    def load_data(self):
        # 用于存储已经创建的分类项
        labels = {}
        self.tasklist = query_AgentTask(label=True,is_first=True, agent_id=self.agent_cfg.user_id)
        # 遍历联系人，按label分类
        for record in self.tasklist:
            label = record.label
            if label is None or len(label) == 0:
                label = "无标签"
            # name = record.name

            # 如果分类项不存在，则创建一个新的分类项
            if label not in labels:
                labels[label] = QTreeWidgetItem(self, [label])

            # 创建联系人项，并添加到对应的分类下
            # contact_item = QTreeWidgetItem(labels[label], [name])
            stick_icon = True if record.stick_time is not None else False
            self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

    def addItem(self, name, group_item,id, is_top=False, icon=False):
        if is_top == False:
            # print("not top")
            top_item = QTreeWidgetItem(group_item)
            top_item.setText(0, name[0:50])
            if icon == True:
                top_item.setIcon(0, self.stick_icon)  # 设置第一列的图标
            top_item.setToolTip(0, name)
            top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
            top_item.setTextAlignment(0, 0)
            self.expandAll()

    def reload(self, key_word):
        self.clear()

        self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.load_pop_menu()
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        if key_word.startswith('+++'):
            # 获取上一次的搜索结果并过滤
            filtered_tasklist = [
                record for record in self.tasklist
                if key_word[3:] in record.title or key_word[3:] in record.problem or key_word[3:] in record.answer
            ]
        else:
            self.tasklist = query_AgentTask_Search_Content(
                label = True,agent_id=self.agent_cfg.user_id, title=key_word, problem=key_word, answer=key_word
            )
            filtered_tasklist = self.tasklist

        # 创建一个集合来存储已经处理过的 first_record 记录
        processed_first_records = set()
        labels = {}
        print("label:",len(filtered_tasklist))
        for record in filtered_tasklist:

            if record.is_first and record.id not in processed_first_records:
                # 处理 first_record
                #--> 添加一条 数据
                label = record.label
                if label is None or len(label) == 0:
                    label = "无标签"
                if label not in labels:
                    labels[label] = QTreeWidgetItem(self, [label])
                stick_icon = True if record.stick_time is not None else False
                self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

                # lambda: self.addItemLabel(record,labels)
                # self.addItem(record.title.replace("\n", ""), record.id)
                processed_first_records.add(record.id)
            elif not record.is_first:
                # 查找是否有相同 task_id 且 is_first 为 True 的记录
                first_record = query_AgentTask_Search_First(agent_id=self.agent_cfg.user_id, task_id=record.task_id,label=True)
                if first_record and first_record.id not in processed_first_records:
                    # 处理 first_record
                    # --> 添加一条 数据
                    label = first_record.label
                    if label is None or len(label) == 0:
                        label = "无标签"
                    if label not in labels:
                        labels[label] = QTreeWidgetItem(self, [label])
                    stick_icon = True if record.stick_time is not None else False
                    self.addItem(first_record.title.replace("\n", ""), labels[label], first_record.id, icon=stick_icon)

                    # lambda: self.addItemLabel(record, labels)
                    processed_first_records.add(first_record.id)
        # -->内部函数
        # def addItemLabel():
        #     label = record.label
        #     if label is None or len(label) == 0:
        #         label = "无标签"
        #     if label not in labels:
        #         labels[label] = QTreeWidgetItem(self, [label])
        #     stick_icon = False
        #     if record.stick_time is not None:
        #         stick_icon = True
        #     self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

    def addItemLabel(self,record,labels):
        label = record.label
        if label is None or len(label) == 0:
            label = "无标签"
        if label not in labels:
            labels[label] = QTreeWidgetItem(self, [label])

        stick_icon = True if record.stick_time is not None else False
        self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)



# class TaskListLabel111(QTreeWidget):
#     """TaskList implements the view in a Tree of the Roster"""
#     rename_signal = pyqtSignal(object)
#     label_signal = pyqtSignal(object)
#
#     def __init__(self, parent, agent):
#
#         super(TaskListLabel, self).__init__(parent)
#         print("TaskList parent", parent)
#         self.connection = None
#         self.mainwindow = parent
#         self.agent = agent
#         self.agent_cfg = self.agent.agent_cfg
#         self.current_task_id = ""
#         self.tasks_history = None
#         self.browser_page = None
#         self.is_browser_page_loaded = False
#
#         self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
#         # self.setSortingEnabled(True)#排序
#         # self.sortItems(0, Qt.AscendingOrder)#排序
#         self.buddies = {}
#         self.groups = {}
#         self.tree = {}
#
#         # 创建一个图标
#         self.stick_icon = QIcon(QPixmap('images/start.png'))  # --> 增加一个置顶图标
#
#         self.load_pop_menu()
#
#         self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
#
#         self.load_data()
#
#     # --> 加载 右键菜单
#     def load_pop_menu(self):
#         self.setContextMenuPolicy(Qt.CustomContextMenu)
#         self.menu = QMenu()
#         # --> 增加置顶，取消置顶 操作
#         self.stick_action = QAction(QIcon("images/bookplus.png"), "置顶", self)
#         self.stick_action.triggered.connect(self.stick_item)
#         self.menu.addAction(self.stick_action)
#
#         self.label_action = QAction(QIcon("images/edit.png"), "加标签", self)
#         self.label_action.triggered.connect(self.label_item)
#         self.menu.addAction(self.label_action)
#
#         self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
#         self.rename_action.triggered.connect(self.rename)
#         self.menu.addAction(self.rename_action)
#
#         self.un_stick_action = QAction(QIcon("images/fileminus.png"), "取消置顶", self)
#         self.un_stick_action.triggered.connect(self.un_stick_item)
#         self.menu.addAction(self.un_stick_action)
#
#         self.delete_action = QAction(QIcon("images/delete.png"), "删除", self)
#         self.delete_action.triggered.connect(self.delete_item)
#         self.menu.addAction(self.delete_action)
#         self.customContextMenuRequested.connect(self.context)
#
#     # --> 加载 数据
#     def load_data(self):
#         # 用于存储已经创建的分类项
#         labels = {}
#         self.tasklist = query_AgentTask(is_first=True, agent_id=self.agent_cfg.user_id)
#         # 遍历联系人，按label分类
#         for record in self.tasklist:
#             label = record.label
#             if label is None or len(label) == 0:
#                 label = "无标签"
#             # name = record.name
#
#             # 如果分类项不存在，则创建一个新的分类项
#             if label not in labels:
#                 labels[label] = QTreeWidgetItem(self, [label])
#
#             # 创建联系人项，并添加到对应的分类下
#             # contact_item = QTreeWidgetItem(labels[label], [name])
#             stick_icon = False
#             if record.stick_time is not None:
#                 stick_icon = True
#             self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)
#
#     def addItem(self, name, group_item,id, is_top=False, icon=False):
#         if is_top == False:
#             # print("not top")
#             top_item = QTreeWidgetItem(group_item)
#             top_item.setText(0, name[0:50])
#             if icon == True:
#                 top_item.setIcon(0, self.stick_icon)  # 设置第一列的图标
#             top_item.setToolTip(0, name)
#             top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
#             top_item.setTextAlignment(0, 0)
#             self.expandAll()
#
#     # --> 加载 数据
#     # def load_data(self):
#     #     self.tasklist = query_AgentTask(is_first=True, agent_id=self.agent_cfg.user_id)
#     #     for record in self.tasklist:
#     #         stick_icon = False
#     #         if record.stick_time is not None:
#     #             stick_icon = True
#     #         self.addItem(record.title.replace("\n", ""), record.id, icon=stick_icon)
#
#     def keyPressEvent(self, event):
#         if event.key() == Qt.Key_Delete:
#             item = self.currentItem()
#             if item:
#                 reply = QMessageBox.question(self, '删除确定',
#                                              f"您确定要删除 '{item.text(0)}'?",
#                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#                 if reply == QMessageBox.Yes:
#                     column = 0
#                     id_value = item.data(column, Qt.UserRole)
#                     # 从数据库中删除所有task_id相同的记录
#                     deleteTasksFromDatabase(id_value)
#
#                     index = self.indexOfTopLevelItem(item)
#                     if index != -1:
#                         self.takeTopLevelItem(index)
#                     else:
#                         parent = item.parent()
#                         parent.removeChild(item)
#         else:
#             super(TaskListLabel, self).keyPressEvent(event)
#
#     def scrollContentsBy(self, dx, dy):
#         # 调用父类方法处理滚动
#         super().scrollContentsBy(dx, dy)
#
#         # 判断是否滚动到底部
#         if self.verticalScrollBar().value() == self.verticalScrollBar().maximum():
#             print("Reached bottom!")
#
#     # def addItem(self, name, id, is_top=False, icon=False):
#     #     item_count = self.topLevelItemCount()
#     #
#     #     if item_count == 0:
#     #         group_item = QTreeWidgetItem(self)
#     #         group_item.setText(0, "所有")
#     #     else:
#     #         group_item = self.topLevelItem(0)
#     #     # print("adding item:",name)
#     #
#     #     # top_item = QTreeWidgetItem(group_item)#不要这样构造，这样排序会缺省按字符排序，排序乱了
#     #     top_item = QTreeWidgetItem()
#     #     top_item.setText(0, name[0:50])
#     #     if icon == True:
#     #         top_item.setIcon(0, self.stick_icon)  # 设置第一列的图标
#     #     top_item.setToolTip(0, name)
#     #     top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
#     #     if is_top == False:
#     #         # print("not top")
#     #         group_item.addChild(top_item)
#     #     else:
#     #         print("im toppppppppp....")
#     #         group_item.insertChild(0, top_item)
#     #     top_item.setTextAlignment(0, 0)
#     #
#     #     self.expandAll()
#
#     def context(self, pos):
#         item = self.itemAt(pos)
#
#         self.current_Item = item
#         self.menu.popup(self.mapToGlobal(pos))
#
#     def deselect_all_items(self):
#         iterator = QTreeWidgetItemIterator(self)
#         while iterator.value():
#             iterator.value().setSelected(False)
#             iterator += 1
#
#     def rename(self):
#         self.label_signal.emit(self.currentItem)
#         item = self.current_Item
#
#         column = 0
#         id_value = item.data(column, Qt.UserRole)
#
#         if id_value:
#
#             oldName = item.text(0)
#             newName, ok = QInputDialog.getText(self, "重命名", "新名称:", text=oldName)
#             if ok and newName:
#                 item.setText(0, newName)
#                 column = 0
#                 id_value = item.data(column, Qt.UserRole)
#                 update_AgentTask(id_value, title=newName)
#         else:
#             QMessageBox.critical(None, "警告", "分类名不能重命名", QMessageBox.Ok)
#
#     def label_item(self):
#         self.rename_signal.emit(self.currentItem)
#         item = self.current_Item
#
#         column = 0
#         id_value = item.data(column, Qt.UserRole)
#
#         if id_value:
#             res = query_AgentTask_ById(id_value)
#             if res is not None:
#                 oldName = res.label
#             if oldName is None:
#                 oldName = ""
#             newName, ok = QInputDialog.getText(self, "加标签", "新标签:", text=oldName)
#             if ok and newName:
#                 update_AgentTask(id_value, label=newName)
#         else:
#             QMessageBox.critical(None, "警告", "分类名不能加标签", QMessageBox.Ok)
#
#     def search(self, key_word):
#         print("tasklist searching", key_word)
#         self.reload(key_word)
#
#     def reload(self, key_word):
#         self.clear()
#
#         self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
#         self.buddies = {}
#         self.groups = {}
#         self.tree = {}
#
#         self.load_pop_menu()
#         self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
#
#         if key_word.startswith('+++'):
#             # 获取上一次的搜索结果并过滤
#             filtered_tasklist = [
#                 record for record in self.tasklist
#                 if key_word[3:] in record.title or key_word[3:] in record.problem or key_word[3:] in record.answer
#             ]
#         else:
#             self.tasklist = query_AgentTask_Search_Content(
#                 agent_id=self.agent_cfg.user_id, title=key_word, problem=key_word, answer=key_word
#             )
#             filtered_tasklist = self.tasklist
#
#         # 创建一个集合来存储已经处理过的 first_record 记录
#         processed_first_records = set()
#
#         for record in filtered_tasklist:
#             if record.is_first and record.id not in processed_first_records:
#                 # 处理 first_record
#                 self.addItem(record.title.replace("\n", ""), record.id)
#                 processed_first_records.add(record.id)
#             elif not record.is_first:
#                 # 查找是否有相同 task_id 且 is_first 为 True 的记录
#                 first_record = query_AgentTask_Search_First(agent_id=self.agent_cfg.user_id, task_id=record.task_id)
#                 if first_record and first_record.id not in processed_first_records:
#                     # 处理 first_record
#                     self.addItem(first_record.title.replace("\n", ""), first_record.id)
#                     processed_first_records.add(first_record.id)
#
#     def delete_item(self):
#
#         item = self.current_Item
#         column = 0
#         id_value = item.data(column, Qt.UserRole)
#         print("id_value", id_value)
#
#         if id_value:
#
#             if item:
#                 reply = QMessageBox.question(self, '删除确定',
#                                              f"您确定要删除 '{item.text(0)}'?",
#                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#             if reply == QMessageBox.Yes:
#
#                 # 从数据库中删除所有task_id相同的记录
#                 deleteTasksFromDatabase(id_value)
#
#                 index = self.indexOfTopLevelItem(item)
#                 if index != -1:
#                     self.takeTopLevelItem(index)
#                 else:
#                     parent = item.parent()
#                     parent.removeChild(item)
#         else:
#
#             QMessageBox.critical(None, "警告", "分类不能删除", QMessageBox.Ok)
#
#     # --> 增加 置顶方法
#     def stick_item(self):
#         item = self.current_Item
#         column = 0
#         id_value = item.data(column, Qt.UserRole)
#         print("id_value", id_value)
#         if id_value:
#             if item:
#                 reply = QMessageBox.question(self, '置顶确定',
#                                              f"您确定要置顶 '{item.text(0)}'?",
#                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#             if reply == QMessageBox.Yes:
#                 update_AgentTask_stick(id_value, 1)
#                 index = self.indexOfTopLevelItem(item)
#                 if index == -1:
#                     parent = item.parent()
#                     if parent:
#                         # 获取当前项目的索引
#                         current_index = parent.indexOfChild(item)
#                         # 从父项目中移除当前项目
#                         parent.removeChild(item)
#                         # 将项目插入到父项目的第一个位置
#                         item.setIcon(0, self.stick_icon)
#                         parent.insertChild(0, item)
#         else:
#
#             QMessageBox.critical(None, "警告", "分类不能置顶", QMessageBox.Ok)
#         print("")
#
#     # --> 增加 取消置顶方法
#     def un_stick_item(self):
#         item = self.current_Item
#         column = 0
#         id_value = item.data(column, Qt.UserRole)
#         if id_value:
#             if item:
#                 reply = QMessageBox.question(self, '取消置顶确定',
#                                              f"您确定要取消置顶 '{item.text(0)}'?",
#                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#             if reply == QMessageBox.Yes:
#                 update_AgentTask_stick(id_value, 0)
#                 self.clear()
#                 self.load_data()
#
#         else:
#             QMessageBox.critical(None, "警告", "分类不能取消置顶", QMessageBox.Ok)
#
#     def getInfo(self):
#         pass
#
#     def onLoadFinished(self, success):
#         if success:
#             browser_page = self.browser_page
#             records = self.tasks_history
#             page_index = 1
#             for record in records:
#                 # self.format_text(browser_page, record.problem, record.answer, record.create_time, record.model_name, page_index)
#                 self.format_text(browser_page, record, page_index)
#                 page_index = page_index + 2
#             self.is_browser_page_loaded = True
#             taskpage = self.taskpage
#             taskpage.page_index = page_index - 1
#
#     def on_itemDoubleClicked(self, item, column):
#         print("双击了：", item.text(column))
#         print(column)
#         id_value = item.data(column, Qt.UserRole)
#         print("双击了：", id_value)
#         if id_value == None:
#             return (False)
#
#         records = query_AgentTask_Content(id=id_value)
#         agent = self.agent
#         agentcfg = self.agent_cfg
#
#         self.mainwindow.open_agent_task_chat(agent)
#         agent_chat_window = self.mainwindow.agent_chat_window_list[agentcfg.user_id]
#         taskpage = agent_chat_window.findChild(TaskPage, "TaskPageObject")
#         self.taskpage = taskpage
#
#         task_id = ""
#         if records:
#             task_id = records[0].task_id
#             for record in records:
#                 problem = self.get_record_problem_for_message(record)
#                 taskpage.messages.append({"role": "user", "content": problem})
#                 taskpage.messages.append({"role": "assistant", "content": record.answer})
#
#         taskpage.task_id = task_id
#         taskpage.is_first = False
#         browser_page = taskpage.messageBrowser.page()
#         browser_page.loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理
#         self.browser_page = browser_page
#         self.tasks_history = records
#
#         if taskpage.is_browser_page_loaded == True:  # page是否已经load了
#             self.is_browser_page_loaded = True
#
#         if self.is_browser_page_loaded == True:
#             self.onLoadFinished(True)
#
#         taskpage.messageEdit.setFocus()
#
#     def get_record_problem_for_message(self, record):
#         attachment_doc_content = ""
#         attachment_image_list = []
#         retrieve_doc_content = ""
#         problem = record.problem
#         if record.attachment_list is not None and record.attachment_list != '':
#             attachment_content_list = json.loads(record.attachment_list)
#             attachment_doc_content, attachment_image_list, retrieve_doc_content = get_content_from_attachment_content_list(
#                 attachment_content_list)
#
#         if retrieve_doc_content != "":
#             problem = f'请根据后面提供的背景内容回答问题，回答只能限制在背景内容的范围内，问题是：{problem};供参考的背景内容是：{retrieve_doc_content}'
#
#         if attachment_doc_content != "":
#             problem = f'{problem};为你提供相关附件内容作为参考，以下是具体的附件内容：{attachment_doc_content}'
#
#         if attachment_image_list:
#             # 创建新的列表以包含文本和图像内容
#             new_attachment_list = []
#
#             # 添加 question[-1]["content"] 到新列表
#             new_attachment_list.append({
#                 "type": "text",
#                 "text": problem,
#             })
#
#             # 将图像列表的内容添加到新列表中
#             new_attachment_list.extend(attachment_image_list)
#
#             problem = new_attachment_list
#
#         return problem
#
#     def format_text(self, browser_page, record, page_index=1, user="用户"):
#
#         question = record.problem
#         answer = record.answer
#         create_time = record.create_time
#         model_name = record.model_name
#
#         message = get_user_ask_msg_title_formatted(page_index, create_time)
#         add_msg_to_message_window(browser_page, message, 1)
#
#         # add_msg_to_message_window_and_format(browser_page, question, 2)
#         message = get_user_ask_msg_content_formatted(question)
#         add_msg_to_message_window(browser_page, message, 2)
#
#         directory_path = os.path.join('resource', 'attachment', 'chat', record.task_id)
#         if record.attachment_list:
#             attachments = json.loads(record.attachment_list)
#             filtered_attachments = [attachment[2] for attachment in attachments if attachment[0] != "km"]
#             if filtered_attachments:
#                 add_attachment_to_message_window(browser_page, directory_path, filtered_attachments, 2)
#
#         message = get_agent_reply_msg_title_formatted(model_name, page_index + 1, create_time, False)
#         add_msg_to_message_window(browser_page, message, 1)
#
#         if question.startswith("给我画"):
#             add_msg_to_message_window(browser_page, answer, 2)
#         else:
#             add_msg_to_message_window_with_markdown_and_highlight(browser_page, answer, 2)
#
#     # def reloadok(self, key_word):
#     #     self.clear()
#     #
#     #     self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
#     #     # self.setSortingEnabled(True)#排序
#     #     # self.sortItems(0, Qt.AscendingOrder)#排序
#     #     self.buddies = {}
#     #     self.groups = {}
#     #     self.tree = {}
#     #
#     #     self.setContextMenuPolicy(Qt.CustomContextMenu)
#     #     self.menu = QMenu()
#     #     self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
#     #     self.rename_action.triggered.connect(self.rename)
#     #     self.menu.addAction(self.rename_action)
#     #
#     #     self.delete_action = QAction(QIcon("images/infos.png"), "删除", self)
#     #     self.delete_action.triggered.connect(self.delete_item)
#     #     self.menu.addAction(self.delete_action)
#     #
#     #
#     #
#     #     # self.menu.addAction(QIcon("images/infos.png"), "信息", self.delete_item)
#     #
#     #     self.customContextMenuRequested.connect(self.context)
#     #     self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
#     #
#     #     self.tasklist = query_AgentTask_Search_Content(is_first=True, agent_id=self.agent_cfg.user_id, title=key_word, problem=key_word, answer=key_word)
#     #     for record in self.tasklist:
#     #         self.addItem(record.title.replace("\n", ""), record.id)
#     #         # print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")
#     #
#     # def reloadbakok2(self, key_word):
#     #     self.clear()
#     #
#     #     self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
#     #     # self.setSortingEnabled(True)#排序
#     #     # self.sortItems(0, Qt.AscendingOrder)#排序
#     #     self.buddies = {}
#     #     self.groups = {}
#     #     self.tree = {}
#     #
#     #     self.setContextMenuPolicy(Qt.CustomContextMenu)
#     #     self.menu = QMenu()
#     #     self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
#     #     self.rename_action.triggered.connect(self.rename)
#     #     self.menu.addAction(self.rename_action)
#     #
#     #     self.delete_action = QAction(QIcon("images/infos.png"), "删除", self)
#     #     self.delete_action.triggered.connect(self.delete_item)
#     #     self.menu.addAction(self.delete_action)
#     #
#     #     # self.menu.addAction(QIcon("images/infos.png"), "信息", self.delete_item)
#     #
#     #     self.customContextMenuRequested.connect(self.context)
#     #     self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
#     #
#     #     if key_word.startswith('+++'):
#     #         # 获取上一次的搜索结果并过滤
#     #         filtered_tasklist = [record for record in self.tasklist if key_word[3:] in record.title or key_word[3:] in record.problem or key_word[3:] in record.answer]
#     #     else:
#     #         self.tasklist = query_AgentTask_Search_Content(is_first=True, agent_id=self.agent_cfg.user_id, title=key_word, problem=key_word, answer=key_word)
#     #         filtered_tasklist = self.tasklist
#     #
#     #     for record in filtered_tasklist:
#     #         self.addItem(record.title.replace("\n", ""), record.id)
#     #         # print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")
