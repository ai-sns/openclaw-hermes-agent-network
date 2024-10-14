from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt

from ui.ui_AddBuddyDialog import Ui_AddBuddyDialog
import xmpp

class AddBuddyDialog(QDialog, Ui_AddBuddyDialog):
    def __init__(self, parent, jabber, groups, jid="", group=""):
        super(AddBuddyDialog, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.jabber = jabber
        self.jid.setText(jid)
        self.group.addItems(groups)
        self.accepted.connect(self.add)

    def add(self):
        print("accept>>>>>>>>>>>>>>")
        result = xmpp.protocol.Iq(typ='set')
        result.setQueryNS(xmpp.NS_ROSTER)
        print(self.nickname.text())
        print(self.jid.text())
        if self.nickname.text():
            item = xmpp.simplexml.Node(tag="item", attrs={"name": self.nickname.text(), "jid": self.jid.text()})
        else:
            item = xmpp.simplexml.Node(tag="item",
                                       attrs={"jid": self.jid.text()})
        #item.addChild(name="group", payload=self.group.currentText())
        item.addChild(name="group", payload="tmpgroup")
        result.T.query.addChild(node=item)
        self.parent.debug(str(result)+"\n")
        self.jabber.send(result)
        presence = xmpp.protocol.Presence(to=str(self.jid.text()),  typ="subscribe")
        self.parent.debug(str(presence))
        self.jabber.send(presence)
