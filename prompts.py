import sys

from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout, QTableWidget, \
    QTableWidgetItem, QTextEdit, QLineEdit, QHBoxLayout, QHeaderView, QMessageBox, QFormLayout, QComboBox, QToolTip
from PyQt5.QtCore import Qt, QPoint, QTimer
from db.DBFactory import Session, Prompt, query_PluginMng_All,get_prompt_frequent_by_agent_id,query_single_prompt_frequent,add_prompt_frequent
from frequentpromptmng import FreezeTableDialog as FrequentFreezeTableDialog

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
        layout.addRow("*角色名称:", self.title_field)

        self.content_field = QTextEdit()
        layout.addRow("*角色描述:", self.content_field)

        self.question_field = QTextEdit()
        layout.addRow("对话模板:", self.question_field)

        self.tags_field = QLineEdit()
        layout.addRow("标签(用逗号分隔):", self.tags_field)

        self.model_field = QComboBox()
        layout.addRow("适用模型:", self.model_field)
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

        agents = query_PluginMng_All(is_delete=0,plugin_type="LLM_Connector")
        agent_dict = [f"{agent.name}: {agent.version}" for agent in agents]
        self.model_field.addItems(agent_dict)
        self.model_field.setCurrentIndex(-1)   # 设置默认值为null

        if self.prompt:
            self.title_field.setText(self.prompt.title)
            self.content_field.setPlainText(self.prompt.content)
            self.question_field.setPlainText(self.prompt.question)
            self.tags_field.setText(self.prompt.tags)
            if self.prompt.model_name is not None:
                cur_txt = self.prompt.model_name
                index = self.model_field.findText(cur_txt)
                if index >= 0:
                    self.model_field.setCurrentIndex(index)

    def save(self):
        title = self.title_field.text()
        content = self.content_field.toPlainText()
        question = self.question_field.toPlainText()
        tags = self.tags_field.text()
        model_name =  self.model_field.currentText()

        if not title:
            QMessageBox.warning(self, "警告", "角色名称必填")
            return

        if not content:
            QMessageBox.warning(self, "警告", "角色描述必填")
            return

        if self.prompt:
            self.prompt.title = title
            self.prompt.content = content
            self.prompt.question = question
            self.prompt.tags = tags
            self.prompt.model_name = model_name
        else:
            new_prompt = Prompt(title=title, content=content, question=question, tags=tags,model_name =model_name )
            self.session.add(new_prompt)

        self.session.commit()
        self.accept()


class PromptManager(QDialog):
    def __init__(self, taskpage, model_name=""):
        super().__init__()
        self.taskpage = taskpage
        self.model_name = model_name
        print("model_name-->", self.model_name)
        self.setWindowTitle("管理提示词")
        window_width = 1280
        window_height = 680
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['角色名称', '角色描述', '对话模板', '标签', '模型','ID'])
        self.table.setColumnHidden(5,True)
        # 设置选择行为为选中整行
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不允许编辑
        # 连接双击事件
        self.table.itemDoubleClicked.connect(self.modify_prompt)

        self.table.horizontalHeader().setStyleSheet("::section {border-bottom: 1px solid gray;}")

        # Set column widths according to specified proportions

        # total_width = self.table.width()
        self.table.setColumnWidth(0, int(window_width * 0.15))  # 第一列15%
        self.table.setColumnWidth(1, int(window_width * 0.30))  # 第二列30%
        self.table.setColumnWidth(2, int(window_width * 0.30))  # 第三列30%
        self.table.setColumnWidth(3, int(window_width * 0.15))  # 第四列15%
        self.table.setColumnWidth(4, int(window_width * 0.10))  # 第四列10%
        self.table.setColumnWidth(5, int(window_width * 0.01))  # 第五列隐藏
        # Setting stretch for the last section to fill remaining space
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("增加")
        self.modify_btn = QPushButton("修改")
        self.delete_btn = QPushButton("删除")
        self.template_btn = QPushButton("使用角色")
        self.add_frequent_btn = QPushButton("设为常用")
        self.show_frequent_btn = QPushButton("常用列表")
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.reject)  # 连接点击事件到关闭函数
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.modify_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.template_btn)  # 添加按钮到布局
        btn_layout.addWidget(self.add_frequent_btn)  # 添加按钮到布局
        btn_layout.addWidget(self.show_frequent_btn)  # 添加按钮到布局
        btn_layout.addWidget(self.close_btn)  # 添加按钮到布局
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_prompt)
        self.modify_btn.clicked.connect(self.modify_prompt)
        self.delete_btn.clicked.connect(self.delete_prompt)
        self.template_btn.clicked.connect(self.use_template)  # 连接新按钮的槽函数
        self.add_frequent_btn.clicked.connect(self.add_frequent)  # 连接新按钮的槽函数
        self.show_frequent_btn.clicked.connect(self.show_frequent)  # 连接新按钮的槽函数

        self.refresh_table()#加载数据

    def show_frequent(self):

        model = QStandardItemModel()
        records = get_prompt_frequent_by_agent_id(self.taskpage.agent_cfg.user_id)
        header = ["显示", "id", "标题", "内容", "标签"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for record in records:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(str(record["id"]))#注意不能使用数字，否则后面会取不到值
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(record["title"])
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(record["content"])
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            newItem3 = QStandardItem(record["tags"])
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            row += 1

        dialog = FrequentFreezeTableDialog(model, self)
        dialog.exec_()



    def show_tooltip(self,t_object,tooltip_text,seconds=2):

        tooltip_position = t_object.mapToGlobal(t_object.rect().bottomLeft())
        QToolTip.showText(tooltip_position, tooltip_text)

        # 使用定时器在 2 秒后自动隐藏气泡
        QTimer.singleShot(seconds, QToolTip.hideText)

    def add_frequent(self,specify_value=""):
        selected_row = self.table.currentRow()
        if selected_row != -1:
            prompt_id = self.table.item(selected_row, 5).text()
            agent_id = self.taskpage.agent_cfg.user_id
            prompt_frequent = query_single_prompt_frequent(prompt_id=int(prompt_id),belong_to_agent_id=agent_id)
            if not prompt_frequent:#如果没有加入
                add_prompt_frequent(prompt_id=int(prompt_id),position=999,belong_to_agent_id=agent_id)
                if specify_value:
                    self.taskpage.update_prompts_in_combobox(False,specify_value)#是否初始化缺省是false，指定了要使用的角色
                else:
                    self.taskpage.update_prompts_in_combobox()
                self.show_tooltip(self.add_frequent_btn,"设置成功")
            else:
                self.show_tooltip(self.add_frequent_btn, "已在列表中")
                if specify_value:
                    self.taskpage.update_prompts_in_combobox(False,specify_value)#是否初始化缺省是false，指定了要使用的角色
        else:
            QMessageBox.warning(self, "警告", "请先选择一条提示词")

    def use_template(self):

        selected_row = self.table.currentRow()
        if selected_row != -1:
            prompt_id = self.table.item(selected_row, 5).text()
            specify_value = prompt_id
            self.add_frequent(specify_value)
            template_content = self.table.item(selected_row, 2).text()  # 获取对话模板内容
            self.accept()  # 关闭窗口
            self.taskpage.receive_template(template_content)  # 返回内容给主窗口
        else:
            QMessageBox.warning(self, "警告", "请先选择一条提示词")

    def refresh_table(self):
        session = Session()
        prompts = session.query(Prompt).all()

        prompts = [
            result for result in prompts
            if result.model_name is None or self.model_name.startswith(result.model_name)
        ]
        print(len(prompts))
        self.table.setRowCount(len(prompts))

        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(prompt.title))
            self.table.setItem(row, 1, QTableWidgetItem(prompt.content))
            self.table.setItem(row, 2, QTableWidgetItem(prompt.question))
            self.table.setItem(row, 3, QTableWidgetItem(prompt.tags))
            self.table.setItem(row, 4, QTableWidgetItem(prompt.model_name))
            self.table.setItem(row, 5, QTableWidgetItem(str(prompt.id)))

        session.close()
        try:
            self.taskpage.update_prompts_in_combobox()
        except Exception as e:
            print(str(e))

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
            self.table.setItem(row, 4, QTableWidgetItem(prompt.model_name ))
            self.table.setItem(row, 5, QTableWidgetItem(str(prompt.id)))

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
