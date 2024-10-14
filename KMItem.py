from PyQt5.QtWidgets import QTreeWidgetItem, QApplication, QDialog, QVBoxLayout, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QVariant, QSettings

from MessageBox import MessageBox
from AddBuddyDialog import AddBuddyDialog

from jabber import STATUS
from jabber import STATUS_IMAGE
import os
from util import open_file

class KMItem(QTreeWidgetItem):
    """
      KMItem implements the view of a Buddy from the Roster
    """

    dialog = None#一个联系人对应一个dialog
    msg = None

    def __init__(self, parent, name,kmrecord):
        super(KMItem, self).__init__(parent,  [name], QTreeWidgetItem.UserType + 1)

        # QTreeWidgetItem configuration
        self.setFlags(Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)  # we can move a contact
        self.parent = parent
        self.kmrecord = kmrecord
        self.name = name
        



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

    def on_click(self):
        kmrecord = self.kmrecord
        name =self.name
        km_path = kmrecord.kmpath
        file_path = os.path.join(os.getcwd(), "km", km_path, "doc",name)
        open_file(file_path)
        # os.system(f"start {file_path}")



    def __str__(self):
        return u'%s' % self.name
