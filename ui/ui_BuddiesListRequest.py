from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QDialog
from PyQt5.QtCore import Qt

class Ui_BuddiesListRequest(object):
    def setupUi(self, BuddiesListRequest):
        BuddiesListRequest.setObjectName("BuddiesListRequest")
        BuddiesListRequest.resize(331, 205)
        BuddiesListRequest.setWindowIcon(QtGui.QIcon("images/aisns.png"))

        self.vboxlayout = QVBoxLayout(BuddiesListRequest)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.label = QLabel(BuddiesListRequest)
        self.label.setPixmap(QtGui.QPixmap("images/aisns.png"))
        self.label.setObjectName("label")
        self.hboxlayout.addWidget(self.label)

        self.jid = QLabel(BuddiesListRequest)
        self.jid.setTextFormat(Qt.AutoText)
        self.jid.setObjectName("jid")
        self.hboxlayout.addWidget(self.jid)

        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.hboxlayout1 = QHBoxLayout()
        self.hboxlayout1.setObjectName("hboxlayout1")

        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.hboxlayout1.addItem(spacerItem1)

        self.textEdit = QTextEdit(BuddiesListRequest)
        self.textEdit.setObjectName("textEdit")
        self.hboxlayout1.addWidget(self.textEdit)
        self.vboxlayout.addLayout(self.hboxlayout1)

        self.hboxlayout2 = QHBoxLayout()
        self.hboxlayout2.setObjectName("hboxlayout2")

        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.hboxlayout2.addItem(spacerItem2)

        self.pushButton = QPushButton(BuddiesListRequest)
        self.pushButton.setDefault(True)
        self.pushButton.setObjectName("pushButton")
        self.hboxlayout2.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton(BuddiesListRequest)
        self.pushButton_2.setObjectName("pushButton_2")
        self.hboxlayout2.addWidget(self.pushButton_2)
        self.vboxlayout.addLayout(self.hboxlayout2)

        self.retranslateUi(BuddiesListRequest)
        self.pushButton.clicked.connect(BuddiesListRequest.accept)
        self.pushButton_2.clicked.connect(BuddiesListRequest.reject)
