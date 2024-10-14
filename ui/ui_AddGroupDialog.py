from PyQt5 import QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDialogButtonBox,QSpacerItem,QSizePolicy
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt


class Ui_AddGroupDialog(object):
    def setupUi(self, AddGroupDialog):
        AddGroupDialog.setObjectName("AddGroupDialog")
        AddGroupDialog.resize(400, 109)
        AddGroupDialog.setWindowIcon(QIcon("images/aisns.png"))

        self.vboxlayout = QVBoxLayout(AddGroupDialog)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.label = QLabel(AddGroupDialog)
        self.label.setPixmap(QPixmap("images/aisns.png"))
        self.label.setObjectName("label")
        self.hboxlayout.addWidget(self.label)

        self.label_2 = QLabel(AddGroupDialog)
        self.label_2.setObjectName("label_2")
        self.hboxlayout.addWidget(self.label_2)

        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.hboxlayout1 = QHBoxLayout()
        self.hboxlayout1.setObjectName("hboxlayout1")

        self.label_3 = QLabel(AddGroupDialog)
        self.label_3.setObjectName("label_3")
        self.hboxlayout1.addWidget(self.label_3)

        self.group = QLineEdit(AddGroupDialog)
        self.group.setObjectName("group")
        self.hboxlayout1.addWidget(self.group)
        self.vboxlayout.addLayout(self.hboxlayout1)

        self.buttonBox = QDialogButtonBox(AddGroupDialog)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)

        #self.retranslateUi(AddGroupDialog)
        self.buttonBox.accepted.connect(AddGroupDialog.accept)
        self.buttonBox.rejected.connect(AddGroupDialog.reject)
