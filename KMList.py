from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from KMItem import KMItem
from KMGroup import KMGroup
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from langchainhandler import *
from db.DBFactory import add_KMData,query_KMData_All,update_KMData,delete_KMData,query_KMData

class KMList(QTreeWidget):
    """KMList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)
    def __init__(self, parent, km_cfg, is_delete=False):

        super(KMList, self).__init__(parent)
        print("KMList parent",parent)
        self.connection = None
        self.mainwindow=parent
        self.km_cfg = km_cfg
        self.is_delete = is_delete

        #
        #
        # # 添加顶层项
        # top_item = QTreeWidgetItem(self)
        # top_item.setText(0, "Top Level Item")
        #
        # # 添加子项
        # child_item = QTreeWidgetItem(top_item)
        # child_item.setText(0, "Child Item")
        #
        # # 添加多个顶层项
        # for i in range(3):
        #     top_item = QTreeWidgetItem(self)
        #     top_item.setText(0, f"Top Level Item {i + 1}")
        #
        # self.expandAll()  # 展开所有项


        #QTreeWidgetItem configuration
        #self.header().setSectionHidden(0, True)
        self.setHeaderLabel("知识列表")#需要设置此处的值，否则缺省值为1
        self.setSortingEnabled(True)
        self.sortItems(0, Qt.AscendingOrder)
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.delete_action = QAction(QIcon("images/delete.png"), "删除", self)
        self.delete_action.triggered.connect(self.delete_item)
        self.menu.addAction(self.delete_action)

        self.customContextMenuRequested.connect(self.context)

        self.offline = True
        self.away = False
        self.kmfilelist=query_KMData_All(km_id=self.km_cfg.km_id, is_delete=self.is_delete)
        for record in self.kmfilelist:
            self.addItem(record.filename, record.id)
            print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")

    def reload(self, key_word=""):
        self.clear()

        self.setHeaderLabel("知识列表")  # 需要设置此处的值，否则缺省值为1
        self.setSortingEnabled(True)
        self.sortItems(0, Qt.AscendingOrder)
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.delete_action = QAction(QIcon("images/delete.png"), "删除", self)
        self.delete_action.triggered.connect(self.delete_item)
        self.menu.addAction(self.delete_action)

        self.customContextMenuRequested.connect(self.context)

        self.offline = True
        self.away = False
        self.kmfilelist = query_KMData_All(km_id=self.km_cfg.km_id, is_delete=self.is_delete)
        for record in self.kmfilelist:
            self.addItem(record.filename, record.id)
            print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")



    def setConnection(self, con):
        self.connection = con
        #一个KMList对应一个用户的ConnectThread



    def addItembak(self, name):
        kmrecord = self.km_cfg
        item_count = self.topLevelItemCount()

        if item_count==0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "所有")
        else:
            group_item = self.topLevelItem(0)

        top_item = KMItem(group_item,name,kmrecord)
        top_item.setText(0, name)
        group_item.addChild(top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()

    def addItem(self, name, id, is_top=False):
        item_count = self.topLevelItemCount()
        kmrecord = self.km_cfg
        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "所有")
        else:
            group_item = self.topLevelItem(0)
        # print("adding item:",name)

        # top_item = QTreeWidgetItem(group_item)#不要这样构造，这样排序会缺省按字符排序，排序乱了

        # top_item = KMItem(group_item, name, kmrecord)
        # top_item.setText(0, name)

        top_item = QTreeWidgetItem()
        top_item.setText(0, name)
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



    def delete_vector(self,filename):

        filepath = os.path.join(os.getcwd(), "km", self.km_cfg.km_id, "doc", filename)
        persist_directory = os.path.join(os.getcwd(), "km", self.km_cfg.km_id, "vector")

        embedding_model_name = self.km_cfg.embeddingmodel

        if embedding_model_name.lower() == "openai":
            emb_type = "openai"
        else:
            emb_type = "other"

        delete_vector(filepath, persist_directory, embedding_model_name, emb_type)


    def delete_item(self):

        item = self.currentItem
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
                km_data = query_KMData(id=id_value)
                filename = km_data.filename
                delete_KMData(id=id_value)
                self.delete_vector(filename)

                index = self.indexOfTopLevelItem(item)
                if index != -1:
                    self.takeTopLevelItem(index)
                else:
                    parent = item.parent()
                    parent.removeChild(item)
        else:
            QMessageBox.critical(None, "警告", "分类不能删除", QMessageBox.Ok)
            return
        self.reload()





    def addGroup(self, group):
        if group:
            if group not in self.groups.keys():
                self.groups[group] = KMGroup(group)
                self.tree[group] = {}
                self.addTopLevelItem(self.groups[group])


    def setOffline(self, hide):
        self.offline = hide
        self.hideGroups()

    def setAway(self, hide):
        self.away = hide
        self.hideGroups()

    def hideGroups(self):
        for child in self.buddies.values():
            if child.isOffline():
                child.setHidden(self.offline)
            elif child.isAway():
                child.setHidden(self.away)
            else:
                child.setHidden(False)

        for group in self.tree.keys():
            hide = True
            for child in self.tree[group].values():
                if not child.isHidden():
                    hide = False
            self.groups[group].setHidden(hide)
        self.expandAll()

    def message(self, event):
        buddy = event.getFrom().getStripped()
        if buddy not in self.buddies.keys():
            self.buddies[buddy] = KMItem(None, buddy)
        self.buddies[buddy].receiveMessage(event)

    def presence(self, jid, status, show=None):
        if jid in self.buddies.keys():
            self.buddies[jid].setStatus(status)
        else:
            time.sleep(2.0)
            self.presence(jid, status, show)
        self.hideGroups()

    def context(self, pos):
        item = self.itemAt(pos)

        self.currentItem = item
        self.menu.popup(self.mapToGlobal(pos))

    def rename(self):
        self.rename_signal.emit(self.currentItem)

    def on_click(self):
        kmrecord = self.km_cfg
        name =self.name
        km_path = kmrecord.kmpath
        file_path = os.path.join(os.getcwd(), "km", km_path, "doc",name)
        open_file(file_path)
        # os.system(f"start {file_path}")

