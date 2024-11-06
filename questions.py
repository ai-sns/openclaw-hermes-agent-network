import sys
import time

from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, QTableWidget, \
    QTableWidgetItem, QTextEdit, QLineEdit, QHBoxLayout, QHeaderView, QMessageBox, QFormLayout, QComboBox, QLabel
from db.DBFactory import Session, Question, query_PluginMng_All
from globals import llm_ability as LLM_Ability_List, question_num, question_prompt, question_type
from aichat import AI_spark


class Worker(QThread):
    finished = pyqtSignal()

    def __init__(self, selection):
        super(Worker, self).__init__()
        self.selection = selection

    def run(self):
        print(f"参数是：{self.selection}")
        self.on_test_model(self.selection)
        self.finished.emit()  # 操作完成后发送信号

        # 创建OpenAI客户端，替换"MOONSHOT_API_KEY"为你的API Key

    def on_test_model(self, selection):
        # print(f"参数是：{param}")
        print("测试操作开始")
        question_type = selection.split(',')[0]
        question_num = selection.split(',')[1]
        prompt = question_prompt
        prompt = prompt.replace("question_num", question_num)
        prompt = prompt.replace("question_type", question_type)
        print("设置按钮被点击")
        spark = AI_spark()
        session = Session()
        # questions = self.read_json("question1.json", "question_1", 2)
        self.qs = [prompt]
        answers = spark.ask_one(prompt)
        self.ans = answers
        print(answers)
        for ans in answers:
            if ans.strip():
                new_question = Question(question=ans, tag=question_type)
                session.add(new_question)
        session.commit()
        session.close()

        # print(list(answers))


class QuestionDialog(QDialog):
    def __init__(self, session, question=None):
        super().__init__()
        self.setWindowTitle("问题")
        window_width = 880
        window_height = 600
        self.resize(window_width, window_height)
        # self.showMaximized()
        self.session = session
        self.question = question

        layout = QFormLayout()

        # self.tag_field = QLineEdit()
        # layout.addRow("标签:", self.tag_field)
        self.tag_field = QComboBox()
        layout.addRow("标签:", self.tag_field)
        self.tag_field.addItems(LLM_Ability_List)
        self.tag_field.setCurrentIndex(-1)  # 设置默认值为null

        self.question_field = QTextEdit()
        layout.addRow("问题:", self.question_field)

        self.id_field = QLineEdit()

        layout.addRow(" ", self.id_field)
        self.id_field.setReadOnly(True)
        # 隐藏QLabel和QLineEdit对象
        self.id_field.hide()

        # self.model_field = QComboBox()
        # layout.addRow("适用模型:", self.model_field)
        # 创建按钮布局
        button_layout = QHBoxLayout()

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save)  # 连接点击事件到保存函数
        button_layout.addWidget(self.save_btn)  # 添加保存按钮到按钮布局

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)  # 连接点击事件到关闭函数
        button_layout.addWidget(self.close_btn)  # 添加关闭按钮到按钮布局

        # 将按钮布局添加到表单布局
        layout.addRow(button_layout)

        self.setLayout(layout)

        if self.question:
            if self.question.tag is not None:
                cur_txt = self.question.tag
                index = self.tag_field.findText(cur_txt)
                if index >= 0:
                    self.tag_field.setCurrentIndex(index)
            self.question_field.setPlainText(self.question.question)
            self.id_field.setText(str(self.question.id))

    def save(self):
        question = self.question_field.toPlainText()
        tag = self.tag_field.currentText()

        if not question or not tag:
            QMessageBox.warning(self, "警告", "所有字段都是必填的")
            return

        if self.question:
            self.question.question = question
            self.question.tag = tag
            # self.question.id = id

        else:
            new_question = Question(question=question, tag=tag)
            self.session.add(new_question)

        self.session.commit()
        self.accept()


class SettingDialog(QDialog):
    user_selected = pyqtSignal(str)  # 使用str而不是QString

    def __init__(self, window_title, label_txt, comb_txt, cur_txt):
        super().__init__()
        self.window_title = window_title
        self.label_txt = label_txt
        self.comb_txt = comb_txt
        self.cur_txt = cur_txt
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

        self.label1 = QLabel("数量", self)
        self.items_field = QLineEdit()
        self.items_field.setText("10")
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
        vbox.addWidget(self.label1)
        vbox.addWidget(self.items_field)

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
        if self.items_field.text() == "":
            user_selection = f'{user_selection},10'
        else:
            user_selection = f'{user_selection},{self.items_field.text()}'

        self.user_selected.emit(user_selection)  # 直接传递Python字符串
        self.accept()  # 使用accept()来关闭模态对话框并返回QDialog.Accepted

    def on_cancel_click(self):
        self.reject()  # 使用reject()来关闭模态对话框并返回QDialog.Rejected


class QuestionManager(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.isdone = False
        self.main_window = main_window

        self.setWindowTitle("管理问题")
        window_width = 1280
        window_height = 680
        self.resize(window_width, window_height)
        # self.showMaximized()
        layout = QVBoxLayout()

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("搜索")
        self.search_field.textChanged.connect(self.search_questions)
        layout.addWidget(self.search_field)

        # Table
        self.table = QTableWidget()
        self.table.setFixedWidth(window_width)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['标签', '问题', 'ID'])
        # 设置选择行为为选中整行
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不允许编辑
        # 连接双击事件
        self.table.itemDoubleClicked.connect(self.modify_question)

        self.table.horizontalHeader().setStyleSheet("::section {border-bottom: 1px solid gray;}")

        # Set column widths according to specified proportions

        # total_width = self.table.width()
        self.table.setColumnWidth(0, int(window_width * 0.20))  # 第一列15%
        self.table.setColumnWidth(1, int(window_width * 0.70))  # 第二列30%
        self.table.setColumnWidth(2, int(window_width * 0.10))  # 第二列30%
        # Setting stretch for the last section to fill remaining space
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.hideColumn(2)
        layout.addWidget(self.table)
        self.setLayout(layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("增加")
        self.add_ai_btn = QPushButton("AI增加")
        self.modify_btn = QPushButton("修改")
        self.delete_btn = QPushButton("删除")
        # self.template_btn = QPushButton("使用模板")  # 新增按钮
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)  # 连接点击事件到关闭函数
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.add_ai_btn)
        btn_layout.addWidget(self.modify_btn)
        btn_layout.addWidget(self.delete_btn)
        # btn_layout.addWidget(self.template_btn)  # 添加按钮到布局
        btn_layout.addWidget(self.close_btn)  # 添加按钮到布局
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_question)
        self.add_ai_btn.clicked.connect(self.add_ai_question)
        self.modify_btn.clicked.connect(self.modify_question)
        self.delete_btn.clicked.connect(self.delete_question)
        # self.template_btn.clicked.connect(self.use_template)  # 连接新按钮的槽函数

        self.refresh_table()

    # def use_template(self):
    #     selected_row = self.table.currentRow()
    #     if selected_row != -1:
    #         template_content = self.table.item(selected_row, 2).text()  # 获取对话模板内容
    #         self.accept()  # 关闭窗口
    #         self.main_window.receive_template(template_content)  # 返回内容给主窗口
    #     else:
    #         QMessageBox.warning(self, "警告", "请先选择一条提示词")

    def refresh_table(self):
        session = Session()
        questions = session.query(Question).all()

        print(len(questions))
        self.table.setRowCount(len(questions))

        for row, question in enumerate(questions):
            self.table.setItem(row, 0, QTableWidgetItem(question.tag))
            self.table.setItem(row, 1, QTableWidgetItem(question.question))
            self.table.setItem(row, 2, QTableWidgetItem(str(question.id)))
            # print("question.id-->", question.id)

        session.close()
        try:
            self.main_window.update_questions_in_combobox()
        except Exception as e:
            print(str(e))

    def add_ai_question(self):
        # dialog = QuestionDialog(session)
        window_title = '自定义'
        label_txt = '能力选项:'
        comb_txt = LLM_Ability_List
        oldName = LLM_Ability_List[0]
        dialog = SettingDialog(window_title, label_txt, comb_txt, oldName)

        def handle_user_selection(selection):
            print(f'主程序接收到用户选择: {selection}')
            self.thread = Worker(selection)
            self.thread.finished.connect(self.on_thread_finished)
            self.thread.start()

        dialog.user_selected.connect(handle_user_selection)
        print("start dialog.exec")
        if dialog.exec_():
            print("dialog.exec")
            pass

    def on_thread_finished(self):
        print("线程完成")
        self.isdone = True
        self.refresh_table()

    def add_question(self):
        session = Session()
        dialog = QuestionDialog(session)
        if dialog.exec_():
            self.refresh_table()
        session.close()

    def modify_question(self):
        try:
            selected_row = self.table.currentRow()
            if selected_row != -1:
                session = Session()
                question_id = int(self.table.item(selected_row, 2).text())
                question = session.query(Question).filter(Question.id == question_id).first()
                dialog = QuestionDialog(session, question)
                if dialog.exec_():
                    self.refresh_table()
                session.close()
            else:
                QMessageBox.warning(self, "警告", "请先选择一条问题")
        except Exception as e:
            print(str(e))

    def delete_question(self):
        selected_rows = list(set(item.row() for item in self.table.selectedItems()))
        if selected_rows:
            session = Session()
            for row in sorted(selected_rows, reverse=True):
                id = self.table.item(row, 2).text()
                question = session.query(Question).filter(Question.id == id).first()
                session.delete(question)
            session.commit()
            session.close()
            self.refresh_table()
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的提示词")

    def search_questions(self):
        keyword = self.search_field.text()
        session = Session()
        questions = session.query(Question).filter(Question.tag.contains(keyword)).all()
        self.table.setRowCount(len(questions))

        for row, question in enumerate(questions):
            self.table.setItem(row, 0, QTableWidgetItem(question.tag))
            self.table.setItem(row, 1, QTableWidgetItem(question.question))
            self.table.setItem(row, 2, QTableWidgetItem(question.id))

        session.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大语音模型提示词管理")
        self.resize(800, 600)

        self.question_combobox = QComboBox(self)
        self.question_combobox.setGeometry(50, 50, 200, 40)
        self.question_combobox.currentIndexChanged.connect(self.print_selected_question)

        self.manage_questions_btn = QPushButton("管理问题", self)
        self.manage_questions_btn.setGeometry(300, 50, 200, 40)
        self.manage_questions_btn.clicked.connect(self.open_question_manager)

        self.update_questions_in_combobox()

    def open_question_manager(self):
        self.question_manager = QuestionManager(self)
        self.question_manager.exec_()

    def update_questions_in_combobox(self):
        pass

    def print_selected_question(self):
        title = self.question_combobox.currentText()
        content = self.question_combobox.currentData()
        print(f"Title: {title}, Content: {content}")

    def receive_template(self, template_content):
        # 处理接收到的模板内容
        print(f"Received Template: {template_content}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
