# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_AboutDialog.ui'
#
# Created: Mon Jan 21 00:21:49 2008
#      by: PyQt5 UI code generator 5.x.x
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        AboutDialog.setObjectName("AboutDialog")
        AboutDialog.resize(QtCore.QSize(QtCore.QRect(0,0,360,231).size()).expandedTo(AboutDialog.minimumSizeHint()))

        self.vboxlayout = QtWidgets.QVBoxLayout(AboutDialog)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        self.aboutIcon = QtWidgets.QLabel(AboutDialog)
        self.aboutIcon.setPixmap(QtGui.QPixmap("images/aisns.png"))
        self.aboutIcon.setObjectName("aboutIcon")
        self.hboxlayout.addWidget(self.aboutIcon)

        self.aboutTitle = QtWidgets.QLabel(AboutDialog)

        font = QtGui.QFont()
        font.setPointSize(24)
        font.setWeight(75)
        font.setBold(True)
        self.aboutTitle.setFont(font)
        self.aboutTitle.setTextFormat(QtCore.Qt.AutoText)
        self.aboutTitle.setObjectName("aboutTitle")
        self.hboxlayout.addWidget(self.aboutTitle)

        spacerItem = QtWidgets.QSpacerItem(40,20,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.aboutTextBrowser = QtWidgets.QTextBrowser(AboutDialog)
        self.aboutTextBrowser.setObjectName("aboutTextBrowser")
        self.vboxlayout.addWidget(self.aboutTextBrowser)

        self.hboxlayout1 = QtWidgets.QHBoxLayout()
        self.hboxlayout1.setObjectName("hboxlayout1")

        spacerItem1 = QtWidgets.QSpacerItem(40,20,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Minimum)
        self.hboxlayout1.addItem(spacerItem1)

        self.closeButton = QtWidgets.QPushButton(AboutDialog)
        self.closeButton.setIcon(QtGui.QIcon("images/close.png"))
        self.closeButton.setObjectName("closeButton")
        self.hboxlayout1.addWidget(self.closeButton)
        self.vboxlayout.addLayout(self.hboxlayout1)

        self.retranslateUi(AboutDialog)
        self.closeButton.clicked.connect(AboutDialog.accept)  # Connect clicked signal using PyQt5 syntax
        QtCore.QMetaObject.connectSlotsByName(AboutDialog)

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QtWidgets.QApplication.translate("AboutDialog", "About Ai-SNS"))
        self.aboutTitle.setText(QtWidgets.QApplication.translate("AboutDialog", "Ai-SNS 0.1"))
        self.aboutTextBrowser.setHtml(QtWidgets.QApplication.translate("AboutDialog", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Ai-SNS is an Ai Agent client in Python.</p>\n"
        "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Programmed by Photon Chen</p></body></html>"))
        self.closeButton.setText(QtWidgets.QApplication.translate("AboutDialog", "Close"))
