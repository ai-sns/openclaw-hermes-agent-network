from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_AddBuddyDialog(object):
    def setupUi(self, AddBuddyDialog):
        AddBuddyDialog.setObjectName("AddBuddyDialog")
        AddBuddyDialog.resize(QtCore.QSize(QtCore.QRect(0, 0, 400, 196).size()).expandedTo(AddBuddyDialog.minimumSizeHint()))
        AddBuddyDialog.setWindowIcon(QtGui.QIcon("images/aisns.png"))

        self.vboxlayout = QtWidgets.QVBoxLayout(AddBuddyDialog)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.label = QtWidgets.QLabel(AddBuddyDialog)
        self.label.setPixmap(QtGui.QPixmap("images/aisns.png").scaled(40,40))
        self.label.setObjectName("label")
        self.hboxlayout.addWidget(self.label)

        self.label_2 = QtWidgets.QLabel(AddBuddyDialog)
        self.label_2.setObjectName("label_2")
        self.hboxlayout.addWidget(self.label_2)

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.gridlayout = QtWidgets.QGridLayout()
        self.gridlayout.setObjectName("gridlayout")

        self.label_3 = QtWidgets.QLabel(AddBuddyDialog)
        self.label_3.setObjectName("label_3")
        self.gridlayout.addWidget(self.label_3, 0, 0, 1, 1)

        self.jid = QtWidgets.QLineEdit(AddBuddyDialog)
        self.jid.setObjectName("jid")
        self.gridlayout.addWidget(self.jid, 0, 1, 1, 1)

        self.nicknameBouh = QtWidgets.QLabel(AddBuddyDialog)
        self.nicknameBouh.setObjectName("nicknameBouh")
        self.gridlayout.addWidget(self.nicknameBouh, 1, 0, 1, 1)

        self.nickname = QtWidgets.QLineEdit(AddBuddyDialog)
        self.nickname.setObjectName("nickname")
        self.gridlayout.addWidget(self.nickname, 1, 1, 1, 1)

        self.label_5 = QtWidgets.QLabel(AddBuddyDialog)
        self.label_5.setObjectName("label_5")
        self.gridlayout.addWidget(self.label_5, 2, 0, 1, 1)

        self.group = QtWidgets.QComboBox(AddBuddyDialog)
        self.group.setObjectName("group")
        self.gridlayout.addWidget(self.group, 2, 1, 1, 1)
        self.vboxlayout.addLayout(self.gridlayout)

        self.buttonBox = QtWidgets.QDialogButtonBox(AddBuddyDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.NoButton | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)

        self.retranslateUi(AddBuddyDialog)
        self.buttonBox.accepted.connect(AddBuddyDialog.accept)
        self.buttonBox.rejected.connect(AddBuddyDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(AddBuddyDialog)

    def retranslateUi(self, AddBuddyDialog):
        _translate = QtCore.QCoreApplication.translate
        AddBuddyDialog.setWindowTitle(_translate("AddBuddyDialog", "添加联系人", None))
        self.label_2.setText(_translate("AddBuddyDialog", "请输入联系人的相关信息", None))
        self.label_3.setText(_translate("AddBuddyDialog", "帐号:", None))
        self.nicknameBouh.setText(_translate("AddBuddyDialog", "昵称:", None))
        self.label_5.setText(_translate("AddBuddyDialog", "组:", None))
