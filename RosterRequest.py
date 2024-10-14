from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal
import xmpp

from ui.ui_BuddiesListRequest import Ui_BuddiesListRequest

class RosterRequest(QDialog, Ui_BuddiesListRequest):
    """BuddyList implements the view in a Tree of the Roster"""

    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, parent, jabber, presence):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.parent = parent
        self.jabber = jabber
        self.jid = presence.getFrom().getStripped()
        self.presence = presence
        if presence.getStatus():
            status = presence.getStatus()
        else:
            status = ""
        self.textEdit.setText(self.jid + " would like to add you on his Buddies List\n\n" + status)

        self.acceptButton.clicked.connect(self.accept)
        self.rejectButton.clicked.connect(self.reject)

    def accept(self):
        reply = xmpp.protocol.Presence(to=self.presence.getFrom().getStripped(), typ="subscribed")
        self.parent.debug(unicode(reply) + "\n")
        self.jabber.send(reply)
        self.accepted.emit()
        self.close()

    def reject(self):
        reply = xmpp.protocol.Presence(to=self.presence.getFrom().getStripped(), typ="unsubscribed")
        self.parent.debug(unicode(reply) + "\n")
        self.jabber.send(reply)
        self.rejected.emit()
        self.close()
