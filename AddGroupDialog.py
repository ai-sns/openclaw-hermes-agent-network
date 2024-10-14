from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt

from ui.ui_AddGroupDialog import Ui_AddGroupDialog
import xmpp

class AddGroupDialog(QDialog, Ui_AddGroupDialog):
    def __init__(self, parent, BuddyList):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setupUi(self)
        self.BuddyList = BuddyList
        self.accepted.connect(self.add)

    def add(self):
        self.BuddyList.addGroup(self.group.text())
