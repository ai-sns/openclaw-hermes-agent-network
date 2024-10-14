# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Ui_MessageWidgetHuman.ui'
#
# Created: Tue Jan 22 07:03:54 2008
#      by: PyQt5 UI code generator 5.15.4
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui,QtWidgets
from PyQt5.QtWidgets import QCheckBox, QLabel
from qtpy.QtCore import Qt, QMetaObject, Signal, Slot, QEvent

class Ui_MessageWidgetHuman(object):
    def setupUi(self, MessageWidget):
        MessageWidget.setObjectName("MessageWidget")
        MessageWidget.resize(QtCore.QSize(QtCore.QRect(0, 0, 400, 300).size()).expandedTo(MessageWidget.minimumSizeHint()))
        MessageWidget.setContentsMargins(0, 0, 0, 0)#不留间隙

        self.vboxlayout = QtWidgets.QVBoxLayout(MessageWidget)
        self.vboxlayout.setObjectName("vboxlayout")
        self.vboxlayout.setContentsMargins(0, 0, 0, 0)#不留间隙


        # 添加标签到布局中
        title_label = QLabel("聊天对象：" + self.name, MessageWidget)
        title_label.setStyleSheet("color: #146ebe;font-weight:bold")
        title_label.setContentsMargins(0, 0, 0, 0)  # 不留间隙
        title_label.setFixedHeight(30)  # 影响间隙


        self.vboxlayout.addWidget(title_label, alignment=Qt.AlignCenter)


        self.messageBrowser = QtWidgets.QTextBrowser(MessageWidget)
        self.messageBrowser.setObjectName("messageBrowser")
        self.vboxlayout.addWidget(self.messageBrowser)

        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)

        self.fontButton = QtWidgets.QPushButton(MessageWidget)
        self.fontButton.setIcon(QtGui.QIcon("images/face.png"))
        self.fontButton.setObjectName("fontButton")
        self.hboxlayout.addWidget(self.fontButton)

        self.videoButton = QtWidgets.QPushButton(MessageWidget)
        self.videoButton.setIcon(QtGui.QIcon("images/attachment.png"))
        self.videoButton.setObjectName("videoButton")
        self.hboxlayout.addWidget(self.videoButton)





        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem1)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.hboxlayout1 = QtWidgets.QHBoxLayout()
        self.hboxlayout1.setObjectName("hboxlayout1")

        # self.messageEdit = QtWidgets.QLineEdit(MessageWidget)

        self.messageEdit = QtWidgets.QTextEdit(MessageWidget)
        self.messageEdit.setFixedHeight(45)  # 假设每行高度为20像素
        self.messageEdit.setStyleSheet("""
            QTextEdit {
                border-radius: 2px; /* 设置圆角 */
                border: 1px solid #c0c0c0; /* 设置边框 */
            }
            QTextEdit:focus {
                border-color: #61addf; /* 设置焦点时的边框颜色 */
            }
        """)

        self.messageEdit.setObjectName("messageEdit")
        self.hboxlayout1.addWidget(self.messageEdit)

        self.sendButton = QtWidgets.QPushButton(MessageWidget)
        self.sendButton.setIcon(QtGui.QIcon("images/sendmessage.png"))
        self.sendButton.setObjectName("sendButton")
        self.hboxlayout1.addWidget(self.sendButton)
        self.vboxlayout.addLayout(self.hboxlayout1)

        self.retranslateUi(MessageWidget)
        QtCore.QMetaObject.connectSlotsByName(MessageWidget)

    def retranslateUi(self, MessageWidget):
        MessageWidget.setWindowTitle(QtCore.QCoreApplication.translate("MessageWidget", "Message", None))
        # self.messageBrowser.setHtml(QtCore.QCoreApplication.translate("MessageWidget", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        # "p, li { white-space: pre-wrap; }\n"
        # "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
        # "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; color:#00008b;\">[14:51] Mauryson :</span><span style=\" color:#00008b;\"> </span><span style=\" color:#000000;\">Salut</span></p>\n"
        # "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; color:#000000;\"><span style=\" font-weight:600; font-style:italic; color:#8b0000;\">[14:52] Natim :</span> Coucou</p></body></html>", None))
        self.messageBrowser.setHtml(QtCore.QCoreApplication.translate("MessageWidget", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
                                                             "p, li { white-space: pre-wrap; }\n"
                                                             "</style></head><body style=\" font-family:\'Microsoft YaHei\'; font-size:14pt; font-weight:400; font-style:normal;\">"
                                                             "</body></html>"))

        self.fontButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "表情", None))
        self.videoButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "附件", None))
        self.sendButton.setText(QtCore.QCoreApplication.translate("MessageWidget", "发送", None))
        # self.sendButton.setShortcut(QtCore.QCoreApplication.translate("MessageWidget", "Return", None))
        self.sendButton.setShortcut(QtGui.QKeySequence(Qt.ControlModifier + Qt.Key_Return))
