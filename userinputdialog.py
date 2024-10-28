import sys
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import pyqtSignal


class UserInputDialog(QDialog):
    user_selected = pyqtSignal(str)  # 使用str而不是QString

    def __init__(self, window_title,label_txt,comb_txt,cur_txt):
        super().__init__()
        self.window_title = window_title
        self.label_txt = label_txt
        self.comb_txt = comb_txt
        self.cur_txt =  cur_txt
        self.initUI()

    def initUI(self):
        # 创建标签
        self.label = QLabel(self.label_txt, self)

        # 创建下拉框，并预设一些选项
        self.combo_box = QComboBox(self)
        # 设置 QComboBox 为可编辑
        self.combo_box.setEditable(True)
        self.combo_box.addItems(self.comb_txt)
        # 设置默认选中值（例如，选中 "Option 2"）
        index = self.combo_box.findText(self.cur_txt)
        if index >= 0:
            self.combo_box.setCurrentIndex(index)

            # 创建按钮
        self.ok_button = QPushButton('OK', self)
        self.cancel_button = QPushButton('Cancel', self)

        # 绑定按钮点击事件到对应的槽函数
        self.ok_button.clicked.connect(self.on_ok_click)
        self.cancel_button.clicked.connect(self.on_cancel_click)

        # 设定垂直布局
        vbox = QVBoxLayout()

        # 将标签和下拉框添加到垂直布局中
        vbox.addWidget(self.label)
        vbox.addWidget(self.combo_box)

        # 设定水平布局以放置按钮
        hbox = QHBoxLayout()
        hbox.addWidget(self.ok_button)
        hbox.addWidget(self.cancel_button)

        # 将水平布局添加到垂直布局的底部
        vbox.addLayout(hbox)

        # 设定窗口的主布局
        self.setLayout(vbox)

        # 使用传入的窗口标题设置窗口的标题
        self.setWindowTitle(self.window_title)

        # 设定窗口的尺寸
        self.setGeometry(300, 300, 300, 100)

    def on_ok_click(self):
        user_selection = self.combo_box.currentText()
        self.user_selected.emit(user_selection)  # 直接传递Python字符串
        self.accept()  # 使用accept()来关闭模态对话框并返回QDialog.Accepted

    def on_cancel_click(self):
        self.reject()  # 使用reject()来关闭模态对话框并返回QDialog.Rejected


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window_title = '自定义用户选择对话框'
    label_txt = '请选择一个选项:'
    comb_txt =  ['选项1', '选项2', '选项3']
    dialog = UserInputDialog(window_title,label_txt,comb_txt,'选项2')


    # 连接信号到槽函数（这里我们仍然使用lambda函数作为示例）
    def handle_user_selection(selection):
        print(f'主程序接收到用户选择: {selection}')
        # 可以在这里添加更多处理逻辑


    dialog.user_selected.connect(handle_user_selection)

    # 以模态方式显示对话框
    if dialog.exec_() == QDialog.Accepted:
        # 这里不需要额外的代码，因为信号已经处理过了
        pass
        # else部分通常不需要，因为reject()不会传递用户选择

    sys.exit(app.exec_())