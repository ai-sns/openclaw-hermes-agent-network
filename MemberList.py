from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from BuddyItem import BuddyItem
from BuddyGroup import BuddyGroup
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from langchainhandler import *
from db.DBFactory import query_MutiAgentCfg, query_AgentCfg, query_AgentCfg_All, update_AgentCfg, delete_AgentCfg
from agentconfigdialog import ConfigDialog as AgentConfigDialog
from Agent import Agent


class MemberList(QTreeWidget):
    """MemberList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)

    def __init__(self, parent, agentcfg):

        super(MemberList, self).__init__(parent)
        print("MemberList parent", parent)
        self.connection = None
        self.mainwindow = parent
        self.agentcfg = agentcfg

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

        # QTreeWidgetItem configuration
        # self.header().setSectionHidden(0, True)
        self.setHeaderLabel("成员列表")  # 需要设置此处的值，否则缺省值为1
        # self.setSortingEnabled(True)#去掉，否则会按字符串排序
        # self.sortItems(0, Qt.AscendingOrder)#去掉，否则会按字符串排序
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)
        self.menu = QMenu()
        # self.rename_action = QAction(QIcon("images/rename.png"), "Rename", self)
        # self.rename_action.triggered.connect(self.rename)
        # self.menu.addAction(self.rename_action)

        self.detail_action = QAction(QIcon("images/namecard.png"), "详细信息", self)
        self.detail_action.triggered.connect(self.getInfo)
        self.menu.addAction(self.detail_action)



        self.customContextMenuRequested.connect(self.context)

        self.offline = True
        self.away = False

        self.selected_agents = self.agentcfg.agents.split(',')  # Assuming index 1 represents selected packages

        agentcommander_user_id = self.agentcfg.agentcommander  # Assuming index 1 represents selected packages

        i = 0

        if agentcommander_user_id:
            selected_agent_cfg = query_AgentCfg(user_id=agentcommander_user_id)
            self.addAgentItem(f"群主-{selected_agent_cfg.name} ({selected_agent_cfg.memo})" if selected_agent_cfg.memo else f"群主-{selected_agent_cfg.name}", agentcommander_user_id)
            i += 1

        if self.selected_agents:
            for selected_agent_user_id in self.selected_agents:
                if selected_agent_user_id:
                    selected_agent_cfg = query_AgentCfg(user_id=selected_agent_user_id)
                    self.addAgentItem(f"{selected_agent_cfg.name} ({selected_agent_cfg.memo})" if selected_agent_cfg.memo else selected_agent_cfg.name, selected_agent_user_id)
                    i += 1

    def addAgentItem(self, name, id, is_top=False):
        item_count = self.topLevelItemCount()

        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "成员")
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

    def addAgentItembak(self, name, user_id, i):
        item_count = i

        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "成员")
        else:
            group_item = self.topLevelItem(0)

        # top_item = QTreeWidgetItem(group_item)#不要这样设置，否则排序乱了
        top_item = QTreeWidgetItem()
        top_item.setText(0, name)
        top_item.setData(0, Qt.UserRole, user_id)
        group_item.addChild(top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()

    def reload(self):
        self.clear()
        agentcfg = query_MutiAgentCfg(group_id=self.agentcfg.group_id)
        self.agentcfg = agentcfg
        self.selected_agents = self.agentcfg.agents.split(',')  # Assuming index 1 represents selected packages

        agentcommander_user_id = self.agentcfg.agentcommander  # Assuming index 1 represents selected packages

        i = 0

        if agentcommander_user_id:
            selected_agent_cfg = query_AgentCfg(user_id=agentcommander_user_id)
            self.addAgentItem(f"群主-{selected_agent_cfg.name} ({selected_agent_cfg.memo})" if selected_agent_cfg.memo else f"群主-{selected_agent_cfg.name}", agentcommander_user_id)
            i += 1

        for selected_agent_user_id in self.selected_agents:
            selected_agent_cfg = query_AgentCfg(user_id=selected_agent_user_id)
            self.addAgentItem(f"{selected_agent_cfg.name} ({selected_agent_cfg.memo})" if selected_agent_cfg.memo else selected_agent_cfg.name, selected_agent_user_id)
            i += 1

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

        item = self.currentItem

        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:

            agent_cfg = query_AgentCfg(user_id=id_value)
            agent = Agent(agent_cfg)

            agentconfigdlg = AgentConfigDialog(self.mainwindow, agent)

            if agentconfigdlg.exec_() == QDialog.Accepted:
                newitemtext = f"{agentconfigdlg.name} ({agentconfigdlg.memo})" if agentconfigdlg.memo else agentconfigdlg.name

                if "群主-" in item.text(column):
                    item.setText(0, "群主-" + newitemtext)
                else:
                    item.setText(0, newitemtext)

    def on_itemDoubleClicked(self, item, column):
        print("双击了：", item.text(column))
        print(column)
        id_value = item.data(column, Qt.UserRole)
        print("双击了：", id_value)
        if id_value == None:
            return (False)

        agent_cfg = query_AgentCfg(user_id=id_value)
        agent = Agent(agent_cfg)

        agentconfigdlg = AgentConfigDialog(self.mainwindow, agent)



        if agentconfigdlg.exec_() == QDialog.Accepted:
            newitemtext=f"{agentconfigdlg.name} ({agentconfigdlg.memo})" if agentconfigdlg.memo else agentconfigdlg.name

            if "群主-" in item.text(column):
                item.setText(0, "群主-"+newitemtext)
            else:
                item.setText(0, newitemtext)


