import os

import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath, QIntValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog)
from db.DBFactory import add_KMCfg,query_KMCfg,query_KMCfg_All,update_KMCfg,delete_KMCfg

import configdialog_rc
import datetime
import random
import string
# from datetime import datetime
class ConfigDialog(QDialog):
    def __init__(self, parent=None,km_cfg=None):
        super(ConfigDialog, self).__init__(parent)

        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(128)
        self.contentsWidget.setSpacing(12)

        self.app = parent
        self.km_cfg = km_cfg


        self.generalPage=GeneralPage(self.km_cfg)
        self.settingPage=SettingPage(self.km_cfg)




        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)
        self.pagesWidget.addWidget(self.settingPage)





        closeButton = QPushButton("Close")

        self.createIcons()
        self.contentsWidget.setCurrentRow(0)

        closeButton.clicked.connect(self.close)

        horizontalLayout = QHBoxLayout()
        horizontalLayout.addWidget(self.contentsWidget)
        horizontalLayout.addWidget(self.pagesWidget, 1)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch(1)
        buttonsLayout.addWidget(closeButton)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(horizontalLayout)
        mainLayout.addStretch(1)
        mainLayout.addSpacing(12)
        #mainLayout.addLayout(buttonsLayout)


        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("确定")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("取消")
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)

        mainLayout.addWidget(button_box)



        self.setLayout(mainLayout)

        self.setWindowTitle("知识库设置")

    def accept_close(self):
        print("accept")

        # generalpage
        name = self.generalPage.nameEdit.text()
        memo = self.generalPage.memoEdit.text()
        label = self.generalPage.labelEdit.text()

        # kmpath = self.settingPage.kmpathEdit.text()
        kmtype = self.settingPage.kmtypeCombo.currentData()

        vectorization=self.settingPage.vectorization_checkbox.isChecked()

        vectortype = self.settingPage.vectortypeCombo.currentText()
        embeddingmodel = self.settingPage.embeddingmodelCombo.currentText()
        textblocklength = self.settingPage.textblocklengthEdit.text()
        overlaplength = self.settingPage.overlaplengthEdit.text()
        titleaugment = self.settingPage.titleaugmentCheckBox.isChecked()

        if self.km_cfg == None:
            idstr = self.generate_random_id()
            kmpath = idstr
            add_KMCfg(idstr, name, memo, label, kmpath,vectorization,kmtype, vectortype, embeddingmodel, textblocklength, overlaplength, titleaugment)

            km_cfg = query_KMCfg(km_id=idstr)
            if kmtype=="0":
                self.app.createToolBoxUnit_KM(km_cfg,1)
            else:
                self.app.createToolBoxUnit_KM_Notes(km_cfg,1)

            self.app.toolBox_KM.setCurrentIndex(self.app.toolBox_KM.count() - 2)
            self.km_cfg = km_cfg



            file_path = os.path.join(os.getcwd(), "km", kmpath, "doc")
            os.makedirs(file_path,exist_ok=True)
            vector_path =os.path.join(os.getcwd(),"km",kmpath,"vector")
            os.makedirs(vector_path, exist_ok=True)

        else:
            update_KMCfg(self.km_cfg.id, name=name, memo=memo, label=label, kmtype=kmtype, vectortype=vectortype, embeddingmodel=embeddingmodel, textblocklength=textblocklength, overlaplength=overlaplength, titleaugment=titleaugment)

        self.accept()
        self.close()

    def reject_close(self):
        print("reject")
        self.close()


    def changePage(self, current, previous):
        if not current:
            current = previous

        self.pagesWidget.setCurrentIndex(self.contentsWidget.row(current))

    def createIcons(self):
        configButton = QListWidgetItem(self.contentsWidget)
        configButton.setIcon(QIcon(':/images/config.png'))
        configButton.setText("基本信息")
        configButton.setTextAlignment(Qt.AlignHCenter)
        configButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        techButton = QListWidgetItem(self.contentsWidget)
        techButton.setIcon(QIcon('images/technique.png'))
        techButton.setText("参数配置")
        techButton.setTextAlignment(Qt.AlignHCenter)
        techButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)




        self.contentsWidget.adjustSize()
        self.contentsWidget.setFixedHeight(500)
        self.contentsWidget.currentItemChanged.connect(self.changePage)

    def generate_random_id(self):
        # 生成随机字母ID，使用大写字母
        random_id = ''.join(random.choices(string.ascii_uppercase, k=2))
        # 获取当前时间
        current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        # 生成随机数
        random_number = ''.join(random.choices(string.digits, k=5))
        # 组合生成的ID
        generated_id = random_id + current_time + random_number
        return generated_id

class GeneralPage(QWidget):
    def __init__(self, agent, parent=None):
        super(GeneralPage, self).__init__(parent)
        self.agent = agent


        packagesGroup = QGroupBox("基本资料")

        self.nameLabel = QLabel("名称:")
        self.nameEdit = QLineEdit()

        self.memoLabel = QLabel("简介:")
        self.memoEdit = QLineEdit()

        self.labelLabel = QLabel("标签:")
        self.labelEdit = QLineEdit()

        if agent!=None:
            self.nameEdit.setText(agent.name)  # Assuming index 0 represents self.nameEdit text
            self.memoEdit.setText(agent.memo)  # Assuming index 1 represents memoEdit text
            self.labelEdit.setText(agent.label)


        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.nameLabel, 0, 0)
        packagesLayout.addWidget(self.nameEdit, 0, 1)
        packagesLayout.addWidget(self.memoLabel, 1, 0)
        packagesLayout.addWidget(self.memoEdit, 1, 1)
        packagesLayout.addWidget(self.labelLabel, 2, 0)
        packagesLayout.addWidget(self.labelEdit, 2, 1)


        packagesGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()

        mainLayout.addWidget(packagesGroup)
        mainLayout.addSpacing(12)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)


class SettingPage(QWidget):
    def __init__(self,agent, parent=None):
        super(SettingPage, self).__init__(parent)
        self.agent = agent

        packagesGroup = QGroupBox("配置信息")


        self.kmpathLabel = QLabel("知识库路径:")
        self.kmpathEdit = QLineEdit()
        self.kmpathEdit.setReadOnly(True)
        self.folderButton = QPushButton("选择")
        self.folderButton.clicked.connect(self.selectFolder)
        self.vlayout = QHBoxLayout()
        self.vlayout.addWidget(self.kmpathEdit)
        self.vlayout.addWidget(self.folderButton)


        self.kmtypeLabel = QLabel("知识库类型:")
        self.kmtypeCombo = QComboBox()
        self.kmtypeCombo.setFixedWidth(250)
        self.kmtypeCombo.addItem("文件","0")
        self.kmtypeCombo.addItem("笔记","1")

        self.vectorization_Label = QLabel("将知识向量化:")
        self.vectorization_checkbox = QCheckBox("是")
        self.vectorization_checkbox.setChecked(True)



        self.vectortypeLabel = QLabel("向量库类型:")
        self.vectortypeCombo = QComboBox()
        self.vectortypeCombo.setFixedWidth(250)
        self.vectortypeCombo.addItem("Chroma")
        self.vectortypeCombo.addItem("faiss")
        self.vectortypeCombo.addItem("milvus")
        self.vectortypeCombo.addItem("zilliz")
        self.vectortypeCombo.addItem("pg")
        self.vectortypeCombo.addItem("es")


        self.embeddingmodelLabel = QLabel("Embedding模型:")
        self.embeddingmodelCombo = QComboBox()
        self.embeddingmodelCombo.setFixedWidth(250)
        self.embeddingmodelCombo.addItem("OpenAI")
        self.embeddingmodelCombo.addItem("text2vec")
        self.embeddingmodelCombo.addItem("text2vec-base")
        self.embeddingmodelCombo.addItem("m3e-small")
        self.embeddingmodelCombo.addItem("m3e-large")
        self.embeddingmodelCombo.addItem("bge-large-zh")
        self.textblocklengthLabel = QLabel("单段文本最大长度:")
        self.textblocklengthEdit = QLineEdit()
        intValidator = QIntValidator()
        self.textblocklengthEdit.setValidator(intValidator)
        self.overlaplengthLabel = QLabel("相邻文本重合长度:")
        self.overlaplengthEdit = QLineEdit()
        intValidator = QIntValidator()
        self.overlaplengthEdit.setValidator(intValidator)
        self.titleaugmentLabel = QLabel("中文标题加强:")
        self.titleaugmentCheckBox = QCheckBox("开启")


        packagesLayout = QGridLayout()
        # packagesLayout.addWidget(self.kmpathLabel, 0, 0)
        # packagesLayout.addLayout(self.vlayout, 0, 1)
        packagesLayout.addWidget(self.kmtypeLabel, 0, 0)
        packagesLayout.addWidget(self.kmtypeCombo, 0, 1)
        packagesLayout.addWidget(self.vectorization_Label, 1, 0)
        packagesLayout.addWidget(self.vectorization_checkbox, 1, 1)
        packagesLayout.addWidget(self.vectortypeLabel, 2, 0)
        packagesLayout.addWidget(self.vectortypeCombo, 2, 1)
        packagesLayout.addWidget(self.embeddingmodelLabel, 3, 0)
        packagesLayout.addWidget(self.embeddingmodelCombo, 3, 1)
        packagesLayout.addWidget(self.textblocklengthLabel, 4, 0)
        packagesLayout.addWidget(self.textblocklengthEdit, 4, 1)
        packagesLayout.addWidget(self.overlaplengthLabel, 5, 0)
        packagesLayout.addWidget(self.overlaplengthEdit, 5, 1)
        packagesLayout.addWidget(self.titleaugmentLabel, 6, 0)
        packagesLayout.addWidget(self.titleaugmentCheckBox, 6, 1)

        packagesGroup.setLayout(packagesLayout)

        if agent != None:
            self.kmpathEdit.setText(agent.kmpath)  # Assuming index 0 represents self.nameEdit text
            if agent.kmtype=="0":
                self.kmtypeCombo.setCurrentText("文件")  # Assuming index 1 represents memoEdit text
            else:
                self.kmtypeCombo.setCurrentText("笔记")  # Assuming index 1 represents memoEdit text
            self.kmtypeCombo.setEnabled(False)

            if agent.vectorization==0:
                self.vectorization_checkbox.setChecked(False)
            else:
                self.vectorization_checkbox.setChecked(True)
            self.vectorization_checkbox.setEnabled(False)

            self.vectortypeCombo.setCurrentText(agent.vectortype)  # Assuming index 1 represents memoEdit text
            self.embeddingmodelCombo.setCurrentText(agent.embeddingmodel)
            self.textblocklengthEdit.setText(str(agent.textblocklength))
            self.overlaplengthEdit.setText(str(agent.overlaplength))
            self.titleaugmentCheckBox.setChecked(agent.titleaugment)

            if agent.vectorization == 0:
                self.vectortypeCombo.setEnabled(False)
                self.embeddingmodelCombo.setEnabled(False)
                self.textblocklengthEdit.setEnabled(False)
                self.overlaplengthEdit.setEnabled(False)
                self.titleaugmentCheckBox.setEnabled(False)






        mainLayout = QVBoxLayout()
        mainLayout.addWidget(packagesGroup)
        mainLayout.addStretch(1)
        self.setLayout(mainLayout)


    def selectFolder(self):
        # 打开文件夹选择框
        folder_path = QFileDialog.getExistingDirectory(self, "请选择文件夹", "")
        if folder_path:
            # 如果用户选择了文件夹，将文件夹路径设置为 QLineEdit 的文本
            self.kmpathEdit.setText(folder_path)

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
