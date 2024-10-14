import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QHBoxLayout, QHeaderView, QMessageBox, QFormLayout, QComboBox
from PyQt5.QtCore import Qt
from db.DBFactory import Session, Prompt

class PromptDialog(QDialog):
    def __init__(self, session, prompt=None):
        super().__init__()
        self.setWindowTitle("提示词")
        window_width = 1280
        window_height = 600
        self.resize(window_width, window_height)
        # self.showMaximized()
        self.session = session
        self.prompt = prompt

        layout = QFormLayout()

        self.title_field = QLineEdit()
        layout.addRow("角色名称:", self.title_field)

        self.content_field = QTextEdit()
        layout.addRow("角色描述:", self.content_field)

        self.question_field = QTextEdit()
        layout.addRow("对话模板:", self.question_field)

        self.tags_field = QLineEdit()
        layout.addRow("标签(用逗号分隔):", self.tags_field)



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

        if self.prompt:
            self.title_field.setText(self.prompt.title)
            self.content_field.setPlainText(self.prompt.content)
            self.question_field.setPlainText(self.prompt.question)
            self.tags_field.setText(self.prompt.tags)

    def save(self):
        title = self.title_field.text()
        content = self.content_field.toPlainText()
        question = self.question_field.toPlainText()
        tags = self.tags_field.text()

        if not title or not content or not question or not tags:
            QMessageBox.warning(self, "警告", "所有字段都是必填的")
            return

        if self.prompt:
            self.prompt.title = title
            self.prompt.content = content
            self.prompt.question = question
            self.prompt.tags = tags
        else:
            new_prompt = Prompt(title=title, content=content, question=question, tags=tags)
            self.session.add(new_prompt)

        self.session.commit()
        self.accept()

class PromptManager(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("管理提示词")
        window_width = 1280
        window_height = 600
        self.resize(window_width, window_height)
        # self.showMaximized()
        layout = QVBoxLayout()

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("通过关键字搜索")
        self.search_field.textChanged.connect(self.search_prompts)
        layout.addWidget(self.search_field)

        # Table
        self.table = QTableWidget()
        self.table.setFixedWidth(window_width)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['角色名称', '角色描述', '对话模板(右击问答界面的管理按钮可置入模板)', '标签'])
        # 设置选择行为为选中整行
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不允许编辑
        # 连接双击事件
        self.table.itemDoubleClicked.connect(self.modify_prompt)

        self.table.horizontalHeader().setStyleSheet("::section {border-bottom: 1px solid gray;}")

        # Set column widths according to specified proportions


        # total_width = self.table.width()
        self.table.setColumnWidth(0, int(window_width * 0.15))  # 第一列15%
        self.table.setColumnWidth(1, int(window_width * 0.35))  # 第二列35%
        self.table.setColumnWidth(2, int(window_width * 0.35))  # 第三列35%
        self.table.setColumnWidth(3, int(window_width * 0.15))  # 第四列15%

        # Setting stretch for the last section to fill remaining space
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("增加")
        self.modify_btn = QPushButton("修改")
        self.delete_btn = QPushButton("删除")
        self.template_btn = QPushButton("使用模板")  # 新增按钮
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)  # 连接点击事件到关闭函数
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.modify_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.template_btn)  # 添加按钮到布局
        btn_layout.addWidget(self.close_btn)  # 添加按钮到布局
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_prompt)
        self.modify_btn.clicked.connect(self.modify_prompt)
        self.delete_btn.clicked.connect(self.delete_prompt)
        self.template_btn.clicked.connect(self.use_template)  # 连接新按钮的槽函数

        self.refresh_table()

    def use_template(self):
        selected_row = self.table.currentRow()
        if selected_row != -1:
            template_content = self.table.item(selected_row, 2).text()  # 获取对话模板内容
            self.accept()  # 关闭窗口
            self.main_window.receive_template(template_content)  # 返回内容给主窗口
        else:
            QMessageBox.warning(self, "警告", "请先选择一条提示词")

    def refresh_table(self):
        session = Session()
        prompts = session.query(Prompt).all()
        self.table.setRowCount(len(prompts))

        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(prompt.title))
            self.table.setItem(row, 1, QTableWidgetItem(prompt.content))
            self.table.setItem(row, 2, QTableWidgetItem(prompt.question))
            self.table.setItem(row, 3, QTableWidgetItem(prompt.tags))

        session.close()
        self.main_window.update_prompts_in_combobox()

    def add_prompt(self):
        session = Session()
        dialog = PromptDialog(session)
        if dialog.exec_():
            self.refresh_table()
        session.close()

    def modify_prompt(self):
        selected_row = self.table.currentRow()
        if selected_row != -1:
            session = Session()
            prompt_title = self.table.item(selected_row, 0).text()
            prompt = session.query(Prompt).filter(Prompt.title == prompt_title).first()
            dialog = PromptDialog(session, prompt)
            if dialog.exec_():
                self.refresh_table()
            session.close()
        else:
            QMessageBox.warning(self, "警告", "请先选择一条提示词")

    def delete_prompt(self):
        selected_rows = list(set(item.row() for item in self.table.selectedItems()))
        if selected_rows:
            session = Session()
            for row in sorted(selected_rows, reverse=True):
                title = self.table.item(row, 0).text()
                prompt = session.query(Prompt).filter(Prompt.title == title).first()
                session.delete(prompt)
            session.commit()
            session.close()
            self.refresh_table()
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的提示词")

    def search_prompts(self):
        keyword = self.search_field.text()
        session = Session()
        prompts = session.query(Prompt).filter(Prompt.title.contains(keyword)).all()
        self.table.setRowCount(len(prompts))

        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(prompt.title))
            self.table.setItem(row, 1, QTableWidgetItem(prompt.content))
            self.table.setItem(row, 2, QTableWidgetItem(prompt.question))
            self.table.setItem(row, 3, QTableWidgetItem(prompt.tags))

        session.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大语音模型提示词管理")
        self.resize(800, 600)

        self.prompt_combobox = QComboBox(self)
        self.prompt_combobox.setGeometry(50, 50, 200, 40)
        self.prompt_combobox.currentIndexChanged.connect(self.print_selected_prompt)

        self.manage_prompts_btn = QPushButton("管理提示词", self)
        self.manage_prompts_btn.setGeometry(300, 50, 200, 40)
        self.manage_prompts_btn.clicked.connect(self.open_prompt_manager)

        self.update_prompts_in_combobox()

    def open_prompt_manager(self):
        self.prompt_manager = PromptManager(self)
        self.prompt_manager.exec_()

    def update_prompts_in_combobox(self):
        current_value = self.prompt_combobox.currentText()
        self.prompt_combobox.clear()
        session = Session()
        prompts = session.query(Prompt).all()
        for prompt in prompts:
            self.prompt_combobox.addItem(prompt.title, prompt.content)
        session.close()

        index = self.prompt_combobox.findText(current_value)
        if index != -1:
            self.prompt_combobox.setCurrentIndex(index)

    def print_selected_prompt(self):
        title = self.prompt_combobox.currentText()
        content = self.prompt_combobox.currentData()
        print(f"Title: {title}, Content: {content}")

    def receive_template(self, template_content):
        # 处理接收到的模板内容
        print(f"Received Template: {template_content}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
