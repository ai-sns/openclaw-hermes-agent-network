from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction, QAbstractItemView, QDialogButtonBox, QMessageBox, QCheckBox, QWidget
from db.DBFactory import update_KMCfg_by_kmid,delete_KMCfg

class FreezeTableDialog(QDialog):
    def __init__(self, model,parent=None):
        super(FreezeTableDialog, self).__init__()
        self.model = model
        self.app = parent
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(1, True)
        self.tableView.setColumnWidth(0, 10)  # 设置这一列否则第二列长度过长
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)

        # Add "Select All" checkbox
        select_all_checkbox = QCheckBox("全选", self)
        select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        layout.addWidget(select_all_checkbox)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("关闭")

        button_box.rejected.connect(self.reject_close)

        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("知识库列表")
        self.setWindowIcon(QIcon("images/aisns.png"))
        self.resize(560, 680)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)

    def toggle_select_all(self, state):
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

    def accept_close(self):
        checkbox_states_and_values = []
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                second_column_data = self.model.index(row, 1).data()
                checkbox_states_and_values.append((row, second_column_data))

        if not checkbox_states_and_values:
            QMessageBox.warning(self, "No Selection", "Please select at least one row.")
            return

        print('OK, I accept')
        for row, value in checkbox_states_and_values:
            print(f'Row {row + 1}, Content of the second column: {value}')

        self.accept()

    def reject_close(self):
        print("reject")
        self.reject()#这是系统函数

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

            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            print("second_column_data:",second_column_data)

            agent_user_id=second_column_data

            # 显示确认对话框以确认删除操作
            confirmation = QMessageBox.question(
                self,
                "确认删除",
                "您确定要删除选中的行吗?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes  # 默认按钮
            )

            # 如果用户选择了“是”，则执行删除操作
            if confirmation == QMessageBox.Yes:


                delete_KMCfg(agent_user_id)


                tool_box_item = self.app.toolBox_KM.findChild(QWidget, agent_user_id)
                # self.app.toolBox_AgentChat.setItemText(self.app.toolBox_AgentChat.indexOf(tool_box_item), f"{name} ({memo})" if memo else name)
                # 查找该item在QToolBox中的索引
                item_index = self.app.toolBox_KM.indexOf(tool_box_item)

                # 如果找到了该item，则进行删除
                if item_index != -1:
                    self.app.toolBox_KM.removeItem(item_index)



                rows_to_delete = [index.row() for index in selected_indexes]
                for row in reversed(rows_to_delete):
                    self.model.removeRow(row)
                self.model.layoutChanged.emit()

    def moveSelectedRowsUp(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            if selected_indexes[0].row()==0:
                return
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            name = self.model.index(selected_indexes[0].row(), 2).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data

            item_to_move = self.app.toolBox_KM.findChild(QWidget, agent_user_id)


            if item_to_move:
                current_index = self.app.toolBox_KM.indexOf(item_to_move)  # 获取当前索引
                item_icon = self.app.toolBox_KM.itemIcon(current_index)
                if current_index > 0:  # 确保不是第一个项
                    # 移动项的逻辑
                    self.app.toolBox_KM.removeItem(current_index)  # 移除当前项
                    self.app.toolBox_KM.insertItem(current_index - 1, item_to_move,item_icon, f"{name}")  # 将项插入到前面的位置

                    print(f"已将 'label_2' 移动到索引: {current_index - 1}")



            rows_to_move = [index.row() for index in selected_indexes]
            for row in rows_to_move:
                if row > 0:
                    self.model.insertRow(row - 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_agent_index()

    def moveSelectedRowsDown(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        rows_count=self.model.rowCount()
        if selected_indexes:
            if selected_indexes[0].row()==rows_count-1:
                QMessageBox.warning(self, "提示", "不可移出当前类别所在区域")
                return
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            name = self.model.index(selected_indexes[0].row(), 2).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data

            item_to_move = self.app.toolBox_KM.findChild(QWidget, agent_user_id)

            if item_to_move:
                current_index = self.app.toolBox_KM.indexOf(item_to_move)  # 获取当前索引
                item_icon = self.app.toolBox_KM.itemIcon(current_index)
                # 移动项的逻辑
                self.app.toolBox_KM.removeItem(current_index)  # 移除当前项
                self.app.toolBox_KM.insertItem(current_index + 1, item_to_move, item_icon, f"{name}")  # 将项插入到前面的位置

                print(f"已将 'label_2' 移动到索引: {current_index + 1}")



            rows_to_move = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_move):
                if row < self.model.rowCount() - 1:
                    self.model.insertRow(row + 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_agent_index()

    def update_agent_index(self):
        for row in range(self.model.rowCount()):
            km_id = self.model.index(row, 1).data()
            update_KMCfg_by_kmid(km_id,position=row)

    def on_item_double_clicked(self):
        self.open_agent_cfg()





def main(args):
    def split_and_strip(s, splitter):
        return [s.strip() for s in line.split(splitter)]

    app = QApplication(args)
    model = QStandardItemModel()
    file = QFile(QFileInfo(__file__).absolutePath() + '/grades.txt')
    if file.open(QFile.ReadOnly):
        line = file.readLine(200).decode('utf-8')
        header = split_and_strip(line, ',')
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
                    model.setItem(row, col+1, newItem)
                row += 1
    file.close()

    dialog = FreezeTableDialog(model)
    dialog.exec_()

if __name__ == '__main__':
    import sys
    main(sys.argv)
