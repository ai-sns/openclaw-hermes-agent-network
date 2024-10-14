import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QHBoxLayout, QHeaderView, QMessageBox, QFormLayout, QComboBox
from PyQt5.QtCore import Qt
from db.DBFactory import Session, KeyValue

class KeyValueDialog(QDialog):
    def __init__(self, session, prompt=None):
        super().__init__()
        self.setWindowTitle("键值对")
        window_width = 1280
        window_height = 600
        self.resize(window_width, window_height)
        # self.showMaximized()
        self.session = session
        self.prompt = prompt

        layout = QFormLayout()

        self.title_field = QLineEdit()
        layout.addRow("键名:", self.title_field)

        self.content_field = QTextEdit()
        layout.addRow("数值:", self.content_field)





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
            self.title_field.setText(self.prompt.key)
            self.content_field.setPlainText(self.prompt.value)


    def save(self):
        title = self.title_field.text()
        content = self.content_field.toPlainText()


        if not title or not content:
            QMessageBox.warning(self, "警告", "所有字段都是必填的")
            return

        if self.prompt:
            self.prompt.key = title
            self.prompt.value = content

        else:
            new_prompt = KeyValue(key=title, value=content)
            self.session.add(new_prompt)

        self.session.commit()
        self.accept()

class KeyValueManager(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("管理键值对")
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
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['键名', '数值'])
        # 设置选择行为为选中整行
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不允许编辑
        # 连接双击事件
        self.table.itemDoubleClicked.connect(self.modify_prompt)

        self.table.horizontalHeader().setStyleSheet("::section {border-bottom: 1px solid gray;}")

        # Set column widths according to specified proportions


        # total_width = self.table.width()
        self.table.setColumnWidth(0, int(window_width * 0.5))  # 第一列20%
        self.table.setColumnWidth(1, int(window_width * 0.5))  # 第二列80%


        # Setting stretch for the last section to fill remaining space
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("增加")
        self.modify_btn = QPushButton("修改")
        self.delete_btn = QPushButton("删除")

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)  # 连接点击事件到关闭函数
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.modify_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.close_btn)  # 添加按钮到布局
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_prompt)
        self.modify_btn.clicked.connect(self.modify_prompt)
        self.delete_btn.clicked.connect(self.delete_prompt)

        self.refresh_table()


    def refresh_table(self):
        session = Session()
        prompts = session.query(KeyValue).all()
        self.table.setRowCount(len(prompts))

        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(prompt.key))
            self.table.setItem(row, 1, QTableWidgetItem(prompt.value))


        session.close()


    def add_prompt(self):
        session = Session()
        dialog = KeyValueDialog(session)
        if dialog.exec_():
            self.refresh_table()
        session.close()

    def modify_prompt(self):
        selected_row = self.table.currentRow()
        if selected_row != -1:
            session = Session()
            prompt_title = self.table.item(selected_row, 0).text()
            prompt = session.query(KeyValue).filter(KeyValue.key == prompt_title).first()
            dialog = KeyValueDialog(session, prompt)
            if dialog.exec_():
                self.refresh_table()
            session.close()
        else:
            QMessageBox.warning(self, "警告", "请先选择一条键值对")

    def delete_prompt(self):
        selected_rows = list(set(item.row() for item in self.table.selectedItems()))
        if selected_rows:
            session = Session()
            for row in sorted(selected_rows, reverse=True):
                title = self.table.item(row, 0).text()
                prompt = session.query(KeyValue).filter(KeyValue.key == title).first()
                session.delete(prompt)
            session.commit()
            session.close()
            self.refresh_table()
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的键值对")

    def search_prompts(self):
        keyword = self.search_field.text()
        session = Session()
        prompts = session.query(KeyValue).filter(KeyValue.key.contains(keyword)).all()
        self.table.setRowCount(len(prompts))

        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(prompt.key))
            self.table.setItem(row, 1, QTableWidgetItem(prompt.value))


        session.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大语音模型键值对管理")
        self.resize(800, 600)

        self.prompt_combobox = QComboBox(self)
        self.prompt_combobox.setGeometry(50, 50, 200, 40)
        self.prompt_combobox.currentIndexChanged.connect(self.print_selected_prompt)

        self.manage_prompts_btn = QPushButton("管理键值对", self)
        self.manage_prompts_btn.setGeometry(300, 50, 200, 40)
        self.manage_prompts_btn.clicked.connect(self.open_prompt_manager)

        self.update_prompts_in_combobox()

    def open_prompt_manager(self):
        self.prompt_manager = KeyValueManager(self)
        self.prompt_manager.exec_()

    def update_prompts_in_combobox(self):
        current_value = self.prompt_combobox.currentText()
        self.prompt_combobox.clear()
        session = Session()
        prompts = session.query(KeyValue).all()
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
