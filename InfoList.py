from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from InfoItem import InfoItem
from InfoGroup import InfoGroup
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from db.DBFactory import add_AIChatInform,query_AIChatInform_All,query_AIChatInform,update_AIChatInform,delete_AIChatInform
from  util import generate_random_id

class InfoList(QTreeWidget):
    """InfoList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)
    def __init__(self, parent,ai_chat_cfg):

        super(InfoList, self).__init__(parent)
        print("InfoList parent",parent)
        self.connection = None
        self.mainwindow=parent
        self.ai_chat_cfg = ai_chat_cfg
        #
        #
        # # 添加顶层项
        top_item = QTreeWidgetItem(self)
        top_item.setText(0, "尚未登录")
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
        self.setHeaderLabel("通知列表")#需要设置此处的值，否则缺省值为1
        self.setSortingEnabled(True)
        self.sortItems(0, Qt.AscendingOrder)
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.menu = QMenu()
        # self.rename_action = QAction(QIcon("images/rename.png"), "同意", self)
        # self.rename_action.triggered.connect(self.rename)
        # self.menu.addAction(self.rename_action)
        # self.menu.addAction(QIcon("images/infos.png"), "拒绝", self.getInfo)
        # self.customContextMenuRequested.connect(self.context)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/accept.png"), "同意", self)
        self.rename_action.triggered.connect(self.accept_friend)
        self.menu.addAction(self.rename_action)
        self.menu.addAction(QIcon("images/reject.png"), "拒绝", self.reject_friend)

        self.customContextMenuRequested.connect(self.context)



        self.offline = True
        self.away = False

    def setConnection(self, con):
        self.connection = con
        #一个InfoList对应一个用户的ConnectThread

    def addItembak(self, jid):
        if self.connection:

            item_count = self.topLevelItemCount()
            if item_count > 0:
                if self.topLevelItem(0).text(0)=='等待登录加载中...':
                    self.takeTopLevelItem(0)

            group = self.connection.getGroups(jid)[0]
            self.addGroup(group)
            if jid not in self.buddies.keys():
                self.buddies[jid] = InfoItem(self.groups[group], jid, self.connection,self.mainwindow)
                self.buddies[jid].setName(self.connection.getName(jid))
            self.groups[group].addChild(self.buddies[jid])
            self.tree[group][jid] = self.buddies[jid]

    def re_init(self):
        self.connection = None
        top_item = QTreeWidgetItem(self)
        top_item.setText(0, "尚未登录")

        self.buddies = {}
        self.groups = {}
        self.tree = {}

    def load(self):
        self.clear()
        records=query_AIChatInform_All(status=0)
        i=0
        for record in records:
            self.addItem(record.title,record.inform_id)
            i +=1

        records = query_AIChatInform_All(status=1)
        j = 0
        for record in records:
            self.addItem_handled(record.title, record.inform_id)
            j += 1

    def addItem(self, name, id, is_top=False):
        item_count = self.topLevelItemCount()

        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "未处理")
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

    def addItem_handled(self, name, id, is_top=False):
        item_count = self.topLevelItemCount()

        if item_count == 0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "已处理")
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


    def addGroup(self, group):
        if group:
            if group not in self.groups.keys():
                self.groups[group] = InfoGroup(group)
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
        buddy = event['from']
        print("buddyfull",buddy.full)#yangyang@xabber.de/gajim.CZ6PGQG0
        print("buddyuser", buddy.user)
        print("buddylocal", buddy.local)
        print("buddyusername", buddy.username)
        print("buddydomain", buddy.domain)
        print("buddynode", buddy.node)
        print("buddybare", buddy.bare)#yangyang@xabber.de
        print("buddyresource", buddy.resource)#gajim.CZ6PGQG0
        buddy = buddy.bare
        if buddy not in self.buddies.keys():
            self.buddies[buddy] = InfoItem(None, buddy)
        self.buddies[buddy].receiveMessage(event)

    def send_message(self, jid,content):

        self.buddies[jid].sendMessageByAgent(content)

    def presence(self, jid, status, show=None):
        if jid in self.buddies.keys():
            self.buddies[jid].setStatus(status)
        else:
            time.sleep(2.0)
            self.presence(jid, status, show)
        self.hideGroups()

    def contextbak(self, pos):
        item = self.itemAt(pos)
        if item:
            if item.type() == QTreeWidgetItem.UserType + 1:
                self.currentItem = item
                self.menu.popup(self.mapToGlobal(pos))

    def context(self, pos):
        item = self.itemAt(pos)

        self.current_Item = item
        self.menu.popup(self.mapToGlobal(pos))

    def accept_friend(self):

        item = self.current_Item

        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:
            self.connection.accept_subscription(id_value)
            QMessageBox.information(None, "提示", "已经接受添加好友请求。", QMessageBox.Ok)
        else:
            QMessageBox.critical(None, "警告", "不能对分类进行操作", QMessageBox.Ok)

    def reject_friend(self):
        item = self.current_Item

        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:
            self.connection.reject_subscription(id_value)
            QMessageBox.information(None, "提示", "已经拒绝添加好友请求。", QMessageBox.Ok)
        else:
            QMessageBox.critical(None, "警告", "不能对分类进行操作", QMessageBox.Ok)

    def get_friend_subscribe_request(self, from_jid, request_msg):
        self.topLevelItem(0).setText(0, "全部")
        request_msg=from_jid+"好友添加请求:"+request_msg
        self.addItem(request_msg,from_jid)
        inform_id=generate_random_id()
        title=request_msg
        content=request_msg
        type="1"
        status="0"
        owner_name=self.ai_chat_cfg.nickname
        owner_account=self.ai_chat_cfg.account
        friend_name=from_jid.split("@")[0]
        friend_account=from_jid
        add_AIChatInform(inform_id, title, content, type, status, owner_name, owner_account, friend_name, friend_account)

