from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction, QAbstractItemView, QDialogButtonBox, QMessageBox, QCheckBox, QWidget, QInputDialog
from db.DBFactory import delete_AgentCfg, update_llm_frequent, query_AgentCfg, delete_llm_frequent
from globals import global_agent_list,global_plugin_list,global_buddy_list
from agentconfigdialog import ConfigDialog as AgentConfigDialog
from Agent import Agent
class FreezeTableDialog(QDialog):
    def __init__(self,model,parent=None):
        super(FreezeTableDialog, self).__init__()
        self.model = model
        self.app = parent
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        # 设置表格为不可编辑
        self.tableView.setEditTriggers(QTableView.NoEditTriggers)

        self.tableView.setColumnHidden(1, True)#将id这一列隐藏掉
        self.tableView.setColumnWidth(0, 20)#设置这一列否则第二列长度过长
        self.tableView.doubleClicked.connect(self.on_item_double_clicked)


        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)

        # Add "Select All" checkbox
        # select_all_checkbox = QCheckBox("全选", self)
        # select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        # layout.addWidget(select_all_checkbox)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("关闭")

        button_box.rejected.connect(self.reject_close)

        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("常用模型列表")
        self.setWindowIcon(QIcon("images/aisns.png"))
        self.resize(680, 680)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reorder_rows()

        self.tableView.horizontalHeader().setStretchLastSection(True)  # 使最后一列填满剩余空间
        self.tableView.verticalHeader().setDefaultSectionSize(30)  # 设置行高
        self.tableView.resizeColumnsToContents()  # 调整列宽以适应内容

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
        # self.reject()#这是系统函数
        self.close()
    def showContextMenu(self, pos):
            selected_rows = self.tableView.selectionModel().selectedRows()

            if selected_rows:
                menu = QMenu(self)
                actions = [
                           ("上移", self.moveSelectedRowsUp),
                           ("下移", self.moveSelectedRowsDown),
                           ("打开", self.open_agent_cfg),
                           ("重命名", self.rename),
                           ("从列表中移除", self.deleteSelectedRows),]

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

            record_id=second_column_data

            # 显示确认对话框以确认删除操作
            confirmation = QMessageBox.question(
                self,
                "确认移除",
                "您确定要从列表中移除选中的模型吗?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes  # 默认按钮
            )

            # 如果用户选择了“是”，则执行删除操作
            if confirmation == QMessageBox.Yes:


                delete_llm_frequent(record_id)




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
            memo = self.model.index(selected_indexes[0].row(), 3).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data


            rows_to_move = [index.row() for index in selected_indexes]
            for row in rows_to_move:
                if row > 0:
                    self.model.insertRow(row - 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_llm_index()

    def moveSelectedRowsDown(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        rows_count=self.model.rowCount()
        if selected_indexes:
            if selected_indexes[0].row()==rows_count-1:
                QMessageBox.warning(self, "提示", "不可移出当前类别所在区域")
                return
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            name = self.model.index(selected_indexes[0].row(), 2).data()
            memo = self.model.index(selected_indexes[0].row(), 3).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data

            # item_to_move = self.app.toolBox_AgentChat.findChild(QWidget, agent_user_id)
            #
            # if item_to_move:
            #     current_index = self.app.toolBox_AgentChat.indexOf(item_to_move)  # 获取当前索引
            #     # 移动项的逻辑
            #     self.app.toolBox_AgentChat.removeItem(current_index)  # 移除当前项
            #     self.app.toolBox_AgentChat.insertItem(current_index + 1, item_to_move, QIcon('images/agentsingle.png'), f"{name} ({memo})" if memo else name)  # 将项插入到前面的位置
            #
            #     print(f"已将 'label_2' 移动到索引: {current_index + 1}")



            rows_to_move = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_move):
                if row < self.model.rowCount() - 1:
                    self.model.insertRow(row + 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_llm_index()

    def update_llm_index(self):
        for row in range(self.model.rowCount()):
            agent_id = self.model.index(row, 1).data()
            update_llm_frequent(agent_id,position=row)


    def on_item_double_clicked(self):
        self.open_agent_cfg()


    def open_agent_cfg(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            column =2
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()

            print("second_column_data:",second_column_data)

            agent_user_id=second_column_data

            agent_cfg = query_AgentCfg(user_id=agent_user_id)
            agent = Agent(agent_cfg)

            agentconfigdlg = AgentConfigDialog(self.app, agent)

            if agentconfigdlg.exec_() == QDialog.Accepted:

                self.model.setItem(row, column, QStandardItem(agentconfigdlg.name))
                self.model.setItem(row, column+1, QStandardItem(agentconfigdlg.memo))
                self.model.setItem(row, column+2, QStandardItem(agentconfigdlg.specialization))
                self.model.setItem(row, column+3, QStandardItem(agentconfigdlg.snsaccount))

    def rename(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            column = 2
            id_value = self.model.index(selected_indexes[0].row(), 1).data()
            oldName = self.model.index(selected_indexes[0].row(), 4).data()

            print("second_column_data:", id_value)
            print("oldName:", oldName)
        else:
            return


        # self.rename_signal.emit(self.currentItem)


        if id_value:

            newName, ok = QInputDialog.getText(self, "重命名", "新名称:", text=oldName)
            if ok and newName:
                self.model.setItem(row, 4, QStandardItem(newName))
                update_llm_frequent(id_value, alias_name=newName)
        else:
            QMessageBox.critical(None, "警告", "分类名不能重命名", QMessageBox.Ok)


    def get_checked_count(self):
        checked_count = 0  # 初始化计数器

        # 遍历模型中的所有行
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)  # 假设复选框在第一列
            if checkbox_item is not None and checkbox_item.checkState() == Qt.Checked:
                checked_count += 1  # 如果复选框被选中，计数器加1

        return checked_count  # 返回被选中的复选框数量
    def reorder_rows(self):
        # 存储所有行数据
        all_rows = []
        for row in range(self.model.rowCount()):
            row_data = []
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                if item is not None:
                    row_data.append(item.clone())  # 深复制项目
                else:
                    row_data.append(QStandardItem(''))
            all_rows.append(row_data)

        # 分离已选中和未选中的行
        checked_rows = [row_data for row_data in all_rows if row_data[0].checkState() == Qt.Checked]
        unchecked_rows = [row_data for row_data in all_rows if row_data[0].checkState() == Qt.Unchecked]

        # 清空模型
        self.model.removeRows(0, self.model.rowCount())

        # 添加已选中和未选中的行到模型中
        for row_data in checked_rows + unchecked_rows:
            self.model.appendRow(row_data)



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
