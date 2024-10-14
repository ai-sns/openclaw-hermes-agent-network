from PyQt5.QtWidgets import QTreeWidgetItem, QApplication, QDialog, QVBoxLayout, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QVariant, QSettings

from MessageBox import MessageBox
from AddBuddyDialog import AddBuddyDialog

from jabber import STATUS
from jabber import STATUS_IMAGE
from db.DBFactory import add_AIChatMessages
from util import generate_random_id
class BuddyItem(QTreeWidgetItem):
    """
      BuddyItem implements the view of a Buddy from the Roster
    """

    dialog = None  # 一个联系人对应一个dialog
    msg = None

    def __init__(self, parent, jid, con, mainwindow,ai_chat_cfg):
        super(BuddyItem, self).__init__(parent, [jid], QTreeWidgetItem.UserType + 1)

        # QTreeWidgetItem configuration
        self.setFlags(Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)  # we can move a contact
        self.parent = parent
        self.jid = jid
        self.name = jid
        self.setStatus(STATUS.unavailable)
        self.connectionThread = con
        self.mainwindow = mainwindow
        self.ai_chat_cfg = ai_chat_cfg
        self.is_browser_page_loaded = False
        # self.setObjectName(jid)

    def setStatus(self, status):
        self.status = status
        if self.status not in range(6):
            self.status = STATUS.unavailable
        settings = QSettings("Trunat", "PyTalk")
        settings.beginGroup("preferences")
        repStatus = str(settings.value("images_status", QVariant("images/status/")))
        # fileStatus = str(settings.value(str(self.status), QVariant(STATUS_IMAGE[self.status])))
        fileStatus = str(settings.value(str(self.status), QVariant(STATUS_IMAGE[0])))
        settings.endGroup()
        self.setIcon(0, QIcon(repStatus + fileStatus))

    def setName(self, name):
        if name:
            self.name = name
            self.setText(0, name)

    def getStatus(self):
        return self.status

    def isAway(self):
        return (self.status == STATUS.away or self.status == STATUS.xa)

    def isOffline(self):
        if self.status == STATUS.unavailable:
            return True
        else:
            return False

    def createDialog(self):
        print("in createDialog")
        if not self.dialog:
            self.dialog = QDialog()
            self.dialog.setWindowIcon(QIcon("images/mail.png"))

            self.msg = MessageBox(self.dialog, self.connectionThread, self.jid, self.name,self.ai_chat_cfg)
            layout = QVBoxLayout(self.dialog)
            layout.addWidget(self.msg)
            self.dialog.setLayout(layout)
            self.dialog.setWindowTitle(self.dialog.tr("Chat with ") + self.name)
        # self.dialog.show() #orgok
        # self.dialog.raise_() #orgok
        print("goingaddconver")
        self.mainwindow.conversation_pages.addWidget(self.dialog)
        print("goingaddconver2")
        # self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
        self.mainwindow.conversation_pages.setCurrentWidget(self.dialog)
        print("goingaddconver3")

    def receiveMessage(self, event):
        self.createDialog()
        # self.msg.receiveMessage(event)

        browser_page = self.msg.messageBrowser.page()
        browser_page.loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理
        self.msg.first_event = event

        self.browser_page = browser_page
        self.msg_event = event

        if self.msg.is_browser_page_loaded == True:  # page是否已经load了
            self.is_browser_page_loaded = True

        if self.is_browser_page_loaded == True:
            self.onLoadFinished(True)

    def onLoadFinished(self, success):
        if success:
            browser_page = self.browser_page
            event = self.msg_event
            self.msg.receiveMessage(event)
            self.is_browser_page_loaded = True

            # browser_page = self.messageBrowser.page()
            # self.message_handler.pass_message(message)
            # message="cjrok222222"

            if not event is None:
                message = f"""\n<strong><span style="color: darkblue; font-size:14pt;">{self.name} :</span></strong><br> {event['body']}<br>"""

                # 以下是AI自动对话相关
                # self.current_received_msg = event['body']
                #
                # if self.human_take_over == False:
                #     self.signal_msg_received.emit()

            browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')
            if not self.msg.conversation_id:
                conversation_id = generate_random_id()
                self.msg.conversation_id = conversation_id
                is_first = True
            else:
                is_first = False


            add_AIChatMessages( self.msg.conversation_id,1,event['body'],event['body'],self.ai_chat_cfg.name,self.ai_chat_cfg.account,self.name,self.jid,is_first)


            if self.msg.first_reply:
                message = f"""<strong><span style="color: darkblue; font-size:14pt;">用户 :</span></strong><br> {self.msg.first_reply}<br>"""

                browser_page.runJavaScript('document.getElementById("allcontent").innerHTML +=`' + message + '`')

                add_AIChatMessages( self.msg.conversation_id, 0, event['body'], self.msg.first_reply, self.ai_chat_cfg.name, self.ai_chat_cfg.account, self.name, self.jid, False)

                self.msg.first_reply = ""

            browser_page.runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

    def sendMessageByAgent(self, content):
        self.createDialog()
        self.msg.sendMessage(content)

    def sendMessage(self):
        self.createDialog()

    def __str__(self):
        return u'%s' % self.name
