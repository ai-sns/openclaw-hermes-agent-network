from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt

class KMGroup(QTreeWidgetItem):
    """
      KMGroup implements the view of a Buddy group from the Roster
    """

    def __init__(self, name):
        QTreeWidgetItem.__init__(self, [name], QTreeWidgetItem.UserType + 1)

        self.name = name
        # QTreeWidgetItem configuration
        self.setFlags(Qt.ItemIsDropEnabled | Qt.ItemIsEnabled)  # We can move a contact into

    def isAway(self):
        for child in self.takeChildren():
            if not child.isAway():
                return False
        return True

    def isOffline(self):
        for child in self.takeChildren():
            if not child.isOffline():
                return False
        return True
