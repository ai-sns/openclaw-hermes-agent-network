from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from BuddyItem import BuddyItem
from BuddyGroup import BuddyGroup
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from langchainhandler import *
from db.DBFactory import add_AgentCfg,query_AgentCfg,query_AgentCfg_All,update_AgentCfg,delete_AgentCfg
class TechList(QTreeWidget):
    """TechList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)
    def __init__(self, parent, agent):

        super(TechList, self).__init__(parent)
        print("TechList parent",parent)
        self.connection = None
        self.mainwindow=parent
        self.agent=agent
        self.agent_cfg=self.agent.agent_cfg

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
        self.setHeaderLabel("技能列表")#需要设置此处的值，否则缺省值为1
        # self.setSortingEnabled(True)
        # self.sortItems(0, Qt.AscendingOrder)
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/rename.png"), "Rename", self)
        self.rename_action.triggered.connect(self.rename)
        self.menu.addAction(self.rename_action)
        self.menu.addAction(QIcon("images/infos.png"), "User Infos", self.getInfo)

        self.customContextMenuRequested.connect(self.context)

        self.offline = True
        self.away = False


        self.selected_plugins = self.agent_cfg.plugins.split(',')  # Assuming index 1 represents selected packages


        self.selected_kms = self.agent_cfg.kms.split(',')  # Assuming index 2 represents selected kms


        i=0
        for plugin in self.selected_plugins:
            self.addPluginItem(plugin,i)
            i+=1

        j=0
        for km in self.selected_kms:
            self.addKmItem(km,j)
            j+=1

    def reload(self):
        self.clear()

        self.setHeaderLabel("技能列表")#需要设置此处的值，否则缺省值为1
        # self.setSortingEnabled(True)
        # self.sortItems(0, Qt.AscendingOrder)
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/rename.png"), "Rename", self)
        self.rename_action.triggered.connect(self.rename)
        self.menu.addAction(self.rename_action)
        self.menu.addAction(QIcon("images/infos.png"), "User Infos", self.getInfo)

        self.customContextMenuRequested.connect(self.context)
        self.agent_cfg=self.agent.agent_cfg

        self.selected_plugins = self.agent_cfg.plugins.split(',')  # Assuming index 1 represents selected packages


        self.selected_kms = self.agent_cfg.kms.split(',')  # Assuming index 2 represents selected kms


        i=0
        for plugin in self.selected_plugins:
            print("the plugin:",plugin)
            self.addPluginItem(plugin,i)
            i+=1

        j=0
        for km in self.selected_kms:
            print("the km:",km)
            self.addKmItem(km,j)
            j+=1

    def setConnection(self, con):
        self.connection = con
        #一个TechList对应一个用户的ConnectThread

    def addPluginItem(self, name,i):
        item_count = i

        if item_count==0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "插件")
        else:
            group_item = self.topLevelItem(0)

        top_item = QTreeWidgetItem()
        top_item.setText(0, name)
        group_item.addChild(top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()

    def addKmItem(self, name,j):
        item_count = j

        if item_count==0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "知识库")
        else:
            group_item = self.topLevelItem(1)

        top_item = QTreeWidgetItem()
        top_item.setText(0, name)
        group_item.addChild(top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()


    def addGroup(self, group):
        if group:
            if group not in self.groups.keys():
                self.groups[group] = BuddyGroup(group)
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
            self.buddies[buddy] = BuddyItem(None, buddy)
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

    def getInfo(self):
        question="对经国家、省、市等有关部门认定的企业技术中心及制造业创新中心，奖补政策是怎样的？"
        persist_directory = "C:\\dev\\ai-sns\\PyTalk\\pytalk\\vector_store"
        embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
        result=getvectorkm_String(question,persist_directory,embedding_model_name)
        print(result)
