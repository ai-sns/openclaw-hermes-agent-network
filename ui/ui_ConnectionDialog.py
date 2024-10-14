from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QLineEdit, QCheckBox, QDialogButtonBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings
from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ConnectionDialog(object):
    def setupUi(self, ConnectionDialog):
        ConnectionDialog.setObjectName("ConnectionDialog")
        ConnectionDialog.resize(289, 277)

        self.vboxlayout = QVBoxLayout(ConnectionDialog)
        self.vboxlayout.setObjectName("vboxlayout")

        self.groupBox = QGroupBox(ConnectionDialog)
        self.groupBox.setObjectName("groupBox")

        self.gridlayout = QGridLayout(self.groupBox)
        self.gridlayout.setObjectName("gridlayout")

        self.label = QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)

        self.userID = QLineEdit(self.groupBox)
        self.userID.setObjectName("userID")
        self.gridlayout.addWidget(self.userID, 0, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.password = QLineEdit(self.groupBox)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setObjectName("password")
        self.gridlayout.addWidget(self.password, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(ConnectionDialog)
        self.groupBox_2.setObjectName("groupBox_2")

        self.gridlayout1 = QGridLayout(self.groupBox_2)
        self.gridlayout1.setObjectName("gridlayout1")

        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName("label_3")
        self.gridlayout1.addWidget(self.label_3, 0, 0, 1, 1)

        self.server = QLineEdit(self.groupBox_2)
        self.server.setObjectName("server")
        self.gridlayout1.addWidget(self.server, 0, 1, 1, 2)

        self.label_4 = QLabel(self.groupBox_2)
        self.label_4.setObjectName("label_4")
        self.gridlayout1.addWidget(self.label_4, 1, 0, 1, 1)

        self.port = QLineEdit(self.groupBox_2)
        self.port.setObjectName("port")
        self.gridlayout1.addWidget(self.port, 1, 1, 1, 1)

        self.label_5 = QLabel(self.groupBox_2)
        self.label_5.setObjectName("label_5")
        self.gridlayout1.addWidget(self.label_5, 2, 0, 1, 1)

        self.ressource = QLineEdit(self.groupBox_2)
        self.ressource.setObjectName("ressource")
        self.gridlayout1.addWidget(self.ressource, 2, 1, 1, 2)

        self.useSSL = QCheckBox(self.groupBox_2)
        self.useSSL.setObjectName("useSSL")
        self.gridlayout1.addWidget(self.useSSL, 1, 2, 1, 1)
        self.vboxlayout.addWidget(self.groupBox_2)

        self.buttonBox = QDialogButtonBox(ConnectionDialog)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        ok_button = self.buttonBox.button(QDialogButtonBox.Ok)
        ok_button.setText("确定")
        cancel_button = self.buttonBox.button(QDialogButtonBox.Cancel)
        cancel_button.setText("取消")

        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)

        self.retranslateUi(ConnectionDialog)
        self.buttonBox.accepted.connect(ConnectionDialog.accept)
        self.buttonBox.rejected.connect(ConnectionDialog.reject)
        ConnectionDialog.setWindowTitle("Connection Dialog")
        ConnectionDialog.setWindowIcon(QIcon("your_icon_path"))  # Replace "your_icon_path" with the actual path to your icon
        QtCore.QMetaObject.connectSlotsByName(ConnectionDialog)

    def retranslateUi(self, ConnectionDialog):
        self.groupBox.setTitle("Login's informations")
        self.label.setText("Jabber ID:")
        self.label_2.setText("Password:")
        self.groupBox_2.setTitle("Server's informations")
        self.label_3.setText("Server:")
        self.label_4.setText("Port:")
        self.label_5.setText("Ressource:")
        self.ressource.setText("PyTalk")
        self.useSSL.setText("Using SSL")
