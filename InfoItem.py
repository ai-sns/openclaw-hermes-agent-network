from PyQt5.QtWidgets import QTreeWidgetItem, QApplication, QDialog, QVBoxLayout, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QVariant, QSettings

from MessageBox import MessageBox
from AddBuddyDialog import AddBuddyDialog

from jabber import STATUS
from jabber import STATUS_IMAGE

class InfoItem(QTreeWidgetItem):
    """
      InfoItem implements the view of a Buddy from the Roster
    """

    dialog = None#一个联系人对应一个dialog
    msg = None

    def __init__(self, parent, jid, con,mainwindow):
        super(InfoItem, self).__init__(parent, [jid], QTreeWidgetItem.UserType + 1)

        # QTreeWidgetItem configuration
        self.setFlags(Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)  # we can move a contact
        self.parent = parent
        self.jid = jid
        self.name = jid
        self.setStatus(STATUS.unavailable)
        self.connectionThread = con
        self.mainwindow=mainwindow

    def setStatus(self, status):
        self.status = status
        if self.status not in range(6):
            self.status = STATUS.unavailable
        settings = QSettings("Trunat", "PyTalk")
        settings.beginGroup("preferences")
        repStatus = str(settings.value("images_status", QVariant("images/status/")))
        #fileStatus = str(settings.value(str(self.status), QVariant(STATUS_IMAGE[self.status])))
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

            self.msg = MessageBox(self.dialog, self.connectionThread, self.jid, self.name)
            layout = QVBoxLayout(self.dialog)
            layout.addWidget(self.msg)
            self.dialog.setLayout(layout)
            self.dialog.setWindowTitle(self.dialog.tr("Chat with ") + self.name)
        #self.dialog.show() #orgok
        #self.dialog.raise_() #orgok
        print("goingaddconver")
        self.mainwindow.conversation_pages.addWidget(self.dialog)
        print("goingaddconver2")
        #self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
        self.mainwindow.conversation_pages.setCurrentWidget(self.dialog)
        print("goingaddconver3")

    def receiveMessage(self, event):
        self.createDialog()
        self.msg.receiveMessage(event)

    def sendMessageByAgent(self, content):
        self.createDialog()
        self.msg.sendMessage(content)


    def sendMessage(self):
        self.createDialog()

    def __str__(self):
        return u'%s' % self.name
