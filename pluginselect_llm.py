from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import (QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction,
                             QAbstractItemView, QDialogButtonBox, QMessageBox, QCheckBox,
                             QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QComboBox, QItemDelegate, QWidget, QInputDialog)
from model_metric import ModelEvaluationDialog
from globals import global_plugin_list
from frequentllmmng import FreezeTableDialog as FrequentFreezeTableDialog
from pytalk.db.DBFactory import query_llm_frequents,add_llm_frequent


class ComboBoxDelegate(QItemDelegate):
    def __init__(self, items_per_row, tableView, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.items_per_row = items_per_row
        self.tableView = tableView
        self.combos = {}

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        row = index.row()
        items = self.items_per_row.get(row, ["Default"])  # 默认值防止未定义的行
        combo.addItems(items)
        combo.currentIndexChanged.connect(lambda: self.on_current_index_changed(combo, index))
        # 将combo存储到字典中，键是行索引
        self.combos[index.row()] = combo
        return combo

    def getComboBox(self, row):
        """获取指定行索引的QComboBox对象。"""
        return self.combos.get(row, None)

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        i = editor.findText(value)
        if i == -1:
            i = 0
        editor.setCurrentIndex(i)


    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)

    def on_current_index_changed(self, combo, index):
        name_column_index = index.model().index(index.row(), 2)
        name_column_value = index.model().data(name_column_index)
        version_column_index = index.model().index(index.row(), 5)
        version_column_value = index.model().data(version_column_index)
        selected_value = combo.currentText()
        print(f"Row {index.row()+1}, First Column: {name_column_value}, SelectedA: {selected_value}")
        plugin_full_name = name_column_value
        plug_in = global_plugin_list[plugin_full_name]
        config = plug_in.get_config()
        config['model'] = selected_value
        plug_in.set_config(config)

    def get_current_mode(self,index):
        name_column_index = index.model().index(index.row(), 2)
        name_column_value = index.model().data(name_column_index)
        version_column_index = index.model().index(index.row(), 5)
        version_column_value = index.model().data(version_column_index)
        plugin_full_name = name_column_value
        plug_in = global_plugin_list[plugin_full_name]
        config = plug_in.get_config()
        return config['model']

    def paint(self, painter, option, index):
        if not self.tableView.indexWidget(index):
            combo = QComboBox(self.tableView)
            row = index.row()
            items = self.items_per_row.get(row, ["Default"])  # 默认值防止未定义的行
            combo.addItems(items)
            current_value = index.model().data(index, Qt.EditRole)
            i = combo.findText(current_value)
            if i == -1:
                i = 0
            combo.setCurrentIndex(i)
            combo.currentIndexChanged.connect(lambda: self.on_current_index_changed(combo, index))
            self.tableView.setIndexWidget(index, combo)
            current_model = self.get_current_mode(index)
            combo.setCurrentText(current_model)
            self.combos[index.row()] = combo


class ButtonDelegate(QItemDelegate):
    def __init__(self, tableView, dialog, parent=None):
        super(ButtonDelegate, self).__init__(parent)
        self.tableView = tableView
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        button = QPushButton("配置", parent)
        button.clicked.connect(lambda: self.print_first_column_content(index.row()))
        return button

    def paint(self, painter, option, index):
        if not self.tableView.indexWidget(index):
            button = QPushButton("配置", self.tableView)
            button.clicked.connect(lambda: self.print_first_column_content(index.row()))
            self.tableView.setIndexWidget(index, button)

    def print_first_column_content(self, row):
        model = self.tableView.model()
        name_column_index = model.index(row, 2)  # 第一列的索引
        name_column_content = model.data(name_column_index)  # 获取第一列的内容

        version_column_index = model.index(row, 5)  # 第一列的索引
        version_column_content = model.data(version_column_index)  # 获取第一列的内容
        print(f"Row {row+1}, First Column Content: {name_column_content}")

        plugin_full_name=name_column_content

        delegate = global_plugin_list[plugin_full_name]

        content = delegate.invoke(command=["open_config_dialog"])
        # 调用 repaintDelegates 方法
        self.dialog.repaintDelegates()

class ButtonDelegateFrequent(QItemDelegate):
    def __init__(self, tableView, dialog, parent=None):
        super(ButtonDelegateFrequent, self).__init__(parent)
        self.tableView = tableView
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        button = QPushButton("加入", parent)
        button.clicked.connect(lambda: self.add_to_frequent_list(index.row()))
        return button

    def paint(self, painter, option, index):
        if not self.tableView.indexWidget(index):
            button = QPushButton("加入", self.tableView)
            button.clicked.connect(lambda: self.add_to_frequent_list(index.row()))
            self.tableView.setIndexWidget(index, button)

    def add_to_frequent_list(self, row):
        model = self.tableView.model()
        plugin_id = model.data(model.index(row, 1))
        name = model.data(model.index(row, 2))  # 获取第一列的内容


        # 重新绘制第 5 列的 ComboBoxDelegate
        index = model.index(row, 4)
        self.tableView.setIndexWidget(index, None)
        combo_delegate = self.tableView.itemDelegateForColumn(4)
        model_type = combo_delegate.getComboBox(row).currentText()

        print(f"Row {row+1}, First Column Content: {name}")

        print(f"Row {row + 3}, Third Column Content: {model_type}")

        plugin_full_name=name + ":" + model_type

        alias_name, ok = QInputDialog.getText(None, "请输入简称", "简称:", text=plugin_full_name)
        if ok and alias_name:
            if not alias_name:
                QMessageBox.critical(None, "警告", "简称不能为空", QMessageBox.Ok)
                return

            agent_id = self.dialog.taskpage.agent_cfg.user_id
            record = query_llm_frequents(plugin_id=plugin_id,model_type=model_type,belong_to_agent_id=agent_id)
            if not record:
                add_llm_frequent(plugin_id=plugin_id,name=name,model_type=model_type,alias_name=alias_name,belong_to_agent_id=agent_id,position=999,is_delete=0)


class FreezeTableDialog(QDialog):
    def __init__(self, model,items_per_row,taskpage):
        super(FreezeTableDialog, self).__init__()
        self.model = model
        self.items_per_row = items_per_row
        self.taskpage=taskpage
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        # 隐藏第二列并设置第一列的宽度
        self.tableView.setColumnHidden(0, True)  # 隐藏 选择 列
        self.tableView.setColumnHidden(1, True)  # 隐藏 ID 列
        self.tableView.setColumnWidth(0, 20)

        # 最小宽度设置

        self.tableView.horizontalHeader().setMinimumSectionSize(100)  # 设置所有列的最小宽度为100px
        self.tableView.setColumnWidth(0, 20)

        self.checkbox_states_and_values = []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)

        # Add "Select All" checkbox and "模型评测" button
        h_layout = QHBoxLayout()
        select_all_checkbox = QCheckBox("全选", self)
        select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        select_all_checkbox.setVisible(False)
        # h_layout.addWidget(select_all_checkbox)

        evaluate_button = QPushButton("模型评测", self)
        evaluate_button.setFixedSize(80, 30)  # 固定按钮大小
        evaluate_button.clicked.connect(self.evaluate_model)
        h_layout.addWidget(evaluate_button)

        button_frequent = QPushButton("常用模型列表", self)
        button_frequent.clicked.connect(self.open_frequent_model_dialog)
        h_layout.addWidget(button_frequent)


        # Add a spacer to ensure buttons are left-aligned
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        h_layout.addItem(spacer)

        layout.addLayout(h_layout)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)

        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("请选择模型")
        self.setWindowIcon(QIcon("images/aisns.png"))
        self.resize(1120, 680)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)

        # self.tableView.horizontalHeader().setStretchLastSection(True)  # 使最后一列填满剩余空间
        # self.tableView.verticalHeader().setDefaultSectionSize(30)  # 设置行高
        self.tableView.resizeColumnsToContents()  # 调整列宽以适应内容

    def toggle_select_all(self, state):
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

    def evaluate_model(self):
        print("pingce")
        dialog = ModelEvaluationDialog()
        dialog.exec_()


    def add_to_frequent_list(self, row):
        model = self.model
        plugin_id = model.data(model.index(row, 1))
        name = model.data(model.index(row, 2))  # 获取第一列的内容

        # 重新绘制第 5 列的 ComboBoxDelegate
        index = model.index(row, 4)
        self.tableView.setIndexWidget(index, None)
        combo_delegate = self.tableView.itemDelegateForColumn(4)
        model_type = combo_delegate.getComboBox(row).currentText()

        print(f"Row {row+1}, First Column Content: {name}")

        print(f"Row {row + 3}, Third Column Content: {model_type}")

        plugin_full_name=name + ":" + model_type
        alias_name = plugin_full_name
        agent_id = self.taskpage.agent_cfg.user_id
        record = query_llm_frequents(plugin_id=plugin_id,model_type=model_type,belong_to_agent_id=agent_id)
        if not record:
            add_llm_frequent(plugin_id=plugin_id,name=name,model_type=model_type,alias_name=alias_name,belong_to_agent_id=agent_id,position=999,is_delete=0)

    def open_frequent_model_dialog(self):

        model = QStandardItemModel()
        records = query_llm_frequents(is_delete=0,belong_to_agent_id=self.taskpage.agent_cfg.user_id)
        header = ["显示", "plugin_id", "连接器", "模型", "简称"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for record in records:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(str(record.id))#注意不能使用数字，否则后面会取不到值
            print("record.id:", str(record.id))
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(record.name)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(record.model_type)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            newItem3 = QStandardItem(record.alias_name)
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            row += 1

        dialog = FrequentFreezeTableDialog(model, self)
        dialog.exec_()


    def accept_close(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            rows_selected = [index.row() for index in selected_indexes]
            for row in reversed(rows_selected):
                name = self.model.data(self.model.index(row, 2))  # 获取第一列的内容
                # 重新绘制第 5 列的 ComboBoxDelegate
                index = self.model.index(row, 4)
                self.tableView.setIndexWidget(index, None)
                combo_delegate = self.tableView.itemDelegateForColumn(4)
                model_type = combo_delegate.getComboBox(row).currentText()

                print(f"Row {row + 1}, First Column Content: {name}")

                print(f"Row {row + 3}, Third Column Content: {model_type}")

                plugin_full_name = name + ":" + model_type

                self.checkbox_states_and_values.append(plugin_full_name)
                self.add_to_frequent_list(row)

        print('OK, I accept')

        self.accept()

    def getResult(self):
        """返回用户输入的文本"""
        return self.checkbox_states_and_values

    def reject_close(self):
        print("reject")
        self.reject()

    def showContextMenu(self, pos):
        selected_rows = self.tableView.selectionModel().selectedRows()
        if selected_rows:
            menu = QMenu(self)
            actions = [("删除", self.deleteSelectedRows),
                       ("上移", self.moveSelectedRowsUp),
                       ("下移", self.moveSelectedRowsDown)]

            for action_text, action_method in actions:
                action = QAction(action_text, self)
                action.triggered.connect(action_method)
                menu.addAction(action)

            menu.exec_(self.mapToGlobal(pos))

    def deleteSelectedRows(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            rows_to_delete = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_delete):
                self.model.removeRow(row)
            self.model.layoutChanged.emit()

    def moveSelectedRowsUp(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            rows_to_move = [index.row() for index in selected_indexes]
            for row in rows_to_move:
                if row > 0:
                    # 更新 items_per_row 顺序
                    self.items_per_row[row], self.items_per_row[row - 1] = self.items_per_row[row - 1], self.items_per_row[row]
                    self.model.insertRow(row - 1, self.model.takeRow(row))

            # 重新绘制委托
            self.repaintDelegates()
            self.model.layoutChanged.emit()

    def moveSelectedRowsDown(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            rows_to_move = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_move):
                if row < self.model.rowCount() - 1:
                    # 更新 items_per_row 顺序
                    self.items_per_row[row], self.items_per_row[row + 1] = self.items_per_row[row + 1], self.items_per_row[row]
                    self.model.insertRow(row + 1, self.model.takeRow(row))

            # 重新绘制委托
            self.repaintDelegates()
            self.model.layoutChanged.emit()

    def repaintDelegates(self):
        for row in range(self.model.rowCount()):
            # 重新绘制第 5 列的 ComboBoxDelegate
            index = self.model.index(row, 4)
            self.tableView.setIndexWidget(index, None)
            combo_delegate = self.tableView.itemDelegateForColumn(4)
            combo_delegate.paint(None, None, index)



            # 重新绘制第 6 列的 ButtonDelegate
            index = self.model.index(row, 7)
            self.tableView.setIndexWidget(index, None)
            button_delegate = self.tableView.itemDelegateForColumn(7)
            button_delegate.paint(None, None, index)


def main(args):
    def split_and_strip(s, splitter):
        return [s.strip() for s in line.split(splitter)]

    app = QApplication(args)
    model = QStandardItemModel()
    file = QFile(QFileInfo(__file__).absolutePath() + '/grades.txt')
    if file.open(QFile.ReadOnly):
        line = file.readLine(200).decode('utf-8')
        header = split_and_strip(line, ',')
        header.insert(5, '模型型号')
        header.append('操作')
        model.setHorizontalHeaderLabels(header)
        row = 0
        while file.canReadLine():
            line = file.readLine(200).decode('utf-8')
            if not line.startswith('#') and ',' in line:
                fields = split_and_strip(line, ',')
                # Create a checkbox in the first column
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                model.setItem(row, 0, checkbox_item)
                for col, field in enumerate(fields):
                    newItem = QStandardItem(field)
                    newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)
                    model.setItem(row, col + 1, newItem)

                # Create a combo box for '模型型号'
                combo_item = QStandardItem("gpt-3.5-turbo")
                model.setItem(row, 5, combo_item)

                # Placeholder for button, actual button will be inserted by delegate
                model.setItem(row, 6, QStandardItem())

                row += 1
    file.close()

    # Define items per row for ComboBox
    items_per_row = {
        0: ["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
        1: ["gpt-3.5-turbo22", "gpt-422", "gpt-4o22"],
        2: ["gpt-3.5-turbo23", "gpt-43", "gpt-4o3"],
        3: ["gpt-3.5-turbo4", "gpt-444", "gpt-444"],
        4: ["gpt-3.5-55", "gpt-55", "gpt-55"],
        # Add more rows as needed
    }

    dialog = FreezeTableDialog(model)
    combo_delegate = ComboBoxDelegate(items_per_row, dialog.tableView)
    dialog.tableView.setItemDelegateForColumn(5, combo_delegate)
    button_delegate = ButtonDelegate(dialog.tableView)
    dialog.tableView.setItemDelegateForColumn(6, button_delegate)
    dialog.exec_()


if __name__ == '__main__':
    import sys

    main(sys.argv)
