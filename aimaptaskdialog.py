import webbrowser

import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath, QIntValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog, QSizePolicy, QMessageBox, QTextEdit, QPlainTextEdit)
from db.DBFactory import add_AiChatCfg, query_AiChatCfg, query_AiChatCfg_All, update_AiChatCfg, add_map_task,update_map_task
from db.DBFactory import add_AgentCfg,query_AgentCfg,query_AgentCfg_All,update_AgentCfg,delete_AgentCfg,add_map_task,update_map_task
from agentconfigdialog import ConfigDialog as AgentConfigDialog
import configdialog_rc
import datetime
import random
import string
# from datetime import datetime



class ConfigDialog(QDialog):
    configured = pyqtSignal(str,str,str,str)
    connectcancel = pyqtSignal(str)

    def __init__(self, parent=None, task_record=None):
        super(ConfigDialog, self).__init__(parent)
        print("initialing.....")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.resize(600,100)

        # self.contentsWidget.setStyleSheet("QListWidget{margin-top: -150px; border: solid 1px red;}")

        self.task_record = task_record
        self.app =parent

        self.generalPage = GeneralPage(self.task_record, parent=self.app)


        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)





        horizontalLayout = QHBoxLayout()
        # horizontalLayout.addWidget(self.contentsWidget)
        horizontalLayout.addWidget(self.pagesWidget, 1)



        mainLayout = QVBoxLayout()
        mainLayout.addLayout(horizontalLayout)
        mainLayout.addStretch(1)
        mainLayout.addSpacing(12)
        # mainLayout.addLayout(buttonsLayout)

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

        self.setWindowTitle("指派任务")



    def accept_close(self):
        print("accept")

        # generalpage
        title = self.generalPage.titleEdit.text()
        if not title:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "标题不能为空。")
            return

        detail = self.generalPage.detailEdit.toPlainText()
        if not detail:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "任务内容不能为空。")
            return



        result = self.generalPage.resultEdit.toPlainText()

        comment = self.generalPage.commentEdit.toPlainText()

        if self.generalPage.notfinishRadio.isChecked() == True:
            rating=1
        elif self.generalPage.finishRadio.isChecked() == True:
            rating = 2
        elif self.generalPage.goodjobRadio.isChecked() == True:
            rating=3
        else:
            rating = 0





        # update_AiChatCfg(1, name, memo, borndate, borncontry, language, gender, joinfederation, syncfederation, specialization, plugins, kms, prompt, snsaccount, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, autorunrounds)
        if self.task_record == None:
            idstr = self.generate_random_id()

            record_id=add_map_task(task_id=idstr,title=title,detail=detail,result=result,comment=comment,rating=rating)
            self.app.maptasklist.addItem(title,record_id,True)

            # add_AiChatCfg(idstr, account,password,nickname,sign,status,humantakeover,name,borndate,gender,area,city,address,mail,imaccount,phone,organization,title,orgposition,memo,serveraddress,port,ssl,resource,proxyused,proxyaddress,proxyport,proxyssl,savepasswordlocal,autoconnect,sendreceipt,sendreadflag,sendchatstatus,sendgroupchatstatus,agreeallfriendrequest)
            # ai_chat_cfg=query_AiChatCfg(user_id=idstr)
            # self.app.createToolBoxUnit_AiChat(ai_chat_cfg,1)
            # self.app.toolBox_AiChat.setCurrentIndex(self.app.toolBox_AiChat.count()-2)
            # self.ai_chat_cfg=ai_chat_cfg


        else:
            idstr = self.task_record.id
            update_map_task(self.task_record.id, task_id=idstr, title=title, detail=detail, result=result, comment=comment, rating=rating)

            first_top_level_item = self.app.topLevelItem(0)  # 获取第一个顶级 item
            # 遍历第一个顶级 item 的所有子项
            for index in range(first_top_level_item.childCount()):
                child_item = first_top_level_item.child(index)
                if child_item.data(0, Qt.UserRole) == idstr:  # 检查子 item 的 data
                    item =child_item
                    break

            item.setText(0, title)

            # tool_box_item = self.app.toolBox_AiChat.findChild(QWidget, idstr)
            # self.app.toolBox_AiChat.setItemText(self.app.toolBox_AiChat.indexOf(tool_box_item),"漫游地球-"+nickname)



        # self.configured.emit(self.ai_chat_cfg.user_id, account, password,status)

        self.accept()
        self.close()

    def reject_close(self):
        print("reject")
        self.close()




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
    def __init__(self, task_record, parent=None):
        super(GeneralPage, self).__init__(parent)
        self.task_record = task_record
        self.app =parent



        taskGroup = QGroupBox("任务内容")

        self.titleLabel = QLabel("标题:")
        self.titleEdit = QLineEdit()
        self.detailLabel = QLabel("内容:")
        self.detailEdit = QPlainTextEdit()
        line_height = self.detailEdit.fontMetrics().height()  # 获取当前字体的一行高度
        self.detailEdit.setFixedHeight(line_height * 10)







        resultGroup = QGroupBox("任务结果")





        resultLayout = QGridLayout()

        # 创建反馈标签
        self.resultLabel = QLabel("结果:")
        # 设置标签的大小策略为固定宽度
        self.resultLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # 创建反馈编辑框
        self.resultEdit = QTextEdit()
        # 设置编辑框的大小策略为扩展
        self.resultEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        line_height = self.resultEdit.fontMetrics().height()  # 获取当前字体的一行高度
        self.resultEdit.setFixedHeight(line_height * 10)

        resultLayout.addWidget(self.resultLabel, 0, 0)
        resultLayout.addWidget(self.resultEdit, 0, 1,1,3)

        resultGroup.setLayout(resultLayout)

        commentGroup = QGroupBox("评价与评论:")

        self.commentLabel = QLabel("评论:")
        self.commentEdit = QPlainTextEdit()

        self.commentLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.commentEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


        line_height = self.commentEdit.fontMetrics().height()  # 获取当前字体的一行高度
        self.commentEdit.setFixedHeight(line_height * 10)




        commentLayout = QGridLayout()
        commentLayout.addWidget(self.commentLabel, 0, 0)
        commentLayout.addWidget(self.commentEdit, 0, 1,1,3)

        # 创建人类接管聊天的标签
        self.humantakeoverLabel = QLabel("评分:")

        self.humantakeoverLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)


        # 创建单选框选项：是
        self.notfinishRadio = QRadioButton("没有完成")
        self.notfinishRadio.setObjectName("notfinishRadio")

        # 创建单选框选项：否
        self.finishRadio = QRadioButton("基本完成")
        self.finishRadio.setObjectName("finishRadio")

        # 创建单选框选项：否
        self.goodjobRadio = QRadioButton("准确完成")
        self.goodjobRadio.setObjectName("goodjobRadio")

        # self.humantakeoverNoRadio2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


        # if ai_chat_cfg != None:
        #     if ai_chat_cfg.humantakeover==1:  # Assuming index 0 represents self.nameEdit text
        #         self.humantakeoverYesRadio.setChecked(True)
        #         self.humantakeoverNoRadio.setChecked(False)
        #     else:  # Assuming index 0 represents self.nameEdit text
        #         self.humantakeoverYesRadio.setChecked(False)
        #         self.humantakeoverNoRadio.setChecked(True)
        # else:
        #     self.humantakeoverYesRadio.setChecked(False)
        #     self.humantakeoverNoRadio.setChecked(True)






        # 将标签和单选框添加到布局中
        commentLayout.addWidget(self.humantakeoverLabel, 1, 0)
        commentLayout.addWidget(self.notfinishRadio, 1, 1)  # 添加“是”选项
        commentLayout.addWidget(self.finishRadio, 1, 2)  # 添加“否”选项
        commentLayout.addWidget(self.goodjobRadio, 1, 3)  # 添加“否”选项


        commentGroup.setLayout(commentLayout)









        # startQueryButton = QPushButton("确认更改状态")

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.titleLabel, 0, 0)
        packagesLayout.addWidget(self.titleEdit, 0, 1)

        packagesLayout.addWidget(self.detailLabel, 3, 0)
        packagesLayout.addWidget(self.detailEdit, 3, 1)



        taskGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()



        mainLayout.addWidget(taskGroup)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(resultGroup)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(commentGroup)
        mainLayout.addSpacing(12)

        resultGroup.setHidden(True)
        commentGroup.setHidden(True)
        self.setLayout(mainLayout)

        if task_record != None:
            resultGroup.setHidden(False)
            commentGroup.setHidden(False)
            self.titleEdit.setText(task_record.title)  # Assuming index 0 represents self.nameEdit text
            self.detailEdit.setPlainText(task_record.detail)  # Assuming index 1 represents memoEdit text
            self.resultEdit.setPlainText(task_record.result)  # Assuming index 2 represents self.dateEdit value
            self.commentEdit.setPlainText(task_record.comment)  # Assuming index 3 represents self.bornareaCombo current text
            rating = task_record.rating
            if rating == 1:
                self.notfinishRadio.setChecked(True)
            elif rating == 2:
                self.finishRadio.setChecked(True)
            elif rating == 3:
                self.goodjobRadio.setChecked(True)


    def on_combobox_changed(self, index):
        """
        当QComboBox的选项变化时调用此方法
        :param index: 当前选中项的索引
        """
        # 获取当前选中的选项文本
        cur_nick_name=self.cur_nick_name
        selected_name = self.serverCombo.currentText()
        if selected_name !="N/A" and selected_name!=cur_nick_name:
            agent_belonged = query_AgentCfg(name=selected_name)
            if self.task_record:
                if agent_belonged.snsaccount != "N/A" and agent_belonged.snsaccount != self.titleEdit.text():
                    QMessageBox.information(self, '提示', '该Agent已经分配了其他社交帐号，请选择别的Agent!')
                    self.serverCombo.setCurrentText(cur_nick_name)
            else:
                if agent_belonged.snsaccount != "N/A":
                    QMessageBox.information(self, '提示', '该Agent已经分配了其他社交帐号，请选择别的Agent!')
                    self.serverCombo.setCurrentText(cur_nick_name)
            # else:
            #     self.serverCombo.setCurrentText(selected_name)
            #     snsaccount=self.ai_chat_cfg.account
            #     snsnickname = self.ai_chat_cfg.nickname
            #     update_AgentCfg(agent_belonged.id,snsaccount=snsaccount,snsnickname=snsnickname)







    def setAvatar(self, pixmap):
        size = QSize(70, 70)
        target = QPixmap(size)
        target.fill(Qt.transparent)

        # 绘制圆形头像
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形边框
        pen = QPen(Qt.gray)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(1, 1, size.width() - 2, size.height() - 2)

        # 绘制头像
        clip_path = QPainterPath()
        clip_path.addEllipse(2, 2, size.width() - 4, size.height() - 4)
        painter.setClipPath(clip_path)
        # painter.drawPixmap(5, 5, size.width()-10, size.height()-10, pixmap.scaled(size.width()-10, size.height()-10, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # 将原始图像缩放到适当大小，并放置在中心
        diameter = min(size.width(), size.height())
        scaled_pixmap = pixmap.scaledToWidth(diameter, Qt.SmoothTransformation) if pixmap.width() < pixmap.height() else pixmap.scaledToHeight(diameter, Qt.SmoothTransformation)
        target_rect = QRect((size.width() - scaled_pixmap.width()) // 2, (size.height() - scaled_pixmap.height()) // 2, scaled_pixmap.width(), scaled_pixmap.height())
        painter.drawPixmap(target_rect, scaled_pixmap)

        painter.end()


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
