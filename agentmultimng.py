from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction, QAbstractItemView, QDialogButtonBox, QMessageBox, QCheckBox, QWidget, QPushButton
from db.DBFactory import delete_MutiAgentCfg,update_MutiAgentCfg_by_group_id,query_MutiAgentCfg,query_AgentCfg
from agentmuticonfigdialog import ConfigDialog as AgentMutiConfigDialog
class FreezeTableDialog(QDialog):
    def __init__(self, model,parent=None):
        super(FreezeTableDialog, self).__init__()
        self.model = model
        self.model.itemChanged.connect(self.on_item_changed)
        self.app = parent
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.setEditTriggers(QTableView.NoEditTriggers)
        self.tableView.setColumnHidden(1, True)
        self.tableView.setColumnWidth(0, 10)#设置这一列否则第二列长度过长
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




        # 创建一个按钮框，只包含“关闭”按钮


        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("Agent群列表")
        self.setWindowIcon(QIcon("images/aisns.png"))
        self.resize(560, 680)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reorder_rows()

    def toggle_select_all(self, state):
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

    def accept_closebak(self):
        selected_rows = self.tableView.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a row.")
            return

        checkbox_states = []
        second_column_contents = []
        for index in selected_rows:
            checkbox_item = self.model.item(index.row(), 0)
            checkbox_states.append(checkbox_item.checkState())
            second_column_contents.append(self.model.item(index.row(), 1).text())

        print('OK, I accept')
        print('Checkbox State::', checkbox_states)
        print('Content of the second column in selected rows:', second_column_contents)
        self.accept()#这是系统函数

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
                actions = [("删除", self.deleteSelectedRows),
                           ("上移", self.moveSelectedRowsUp),
                           ("下移", self.moveSelectedRowsDown),
                           ("打开", self.open_agent_cfg)]

                for action_text, action_method in actions:
                    action = QAction(action_text, self)
                    action.triggered.connect(action_method)
                    menu.addAction(action)

                menu.exec_(self.mapToGlobal(pos))

    def deleteSelectedRows(self):
        # 获取用户选中的行
        selected_indexes = self.tableView.selectionModel().selectedRows()

        # 确保用户有选择要删除的行
        if selected_indexes:
            # 获取第二列的数据（假设是要删除的代理组ID）
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            print("second_column_data:", second_column_data)

            agent_group_id = second_column_data

            # 显示确认对话框以确认删除操作
            confirmation = QMessageBox.question(
                self,
                "确认删除",
                "您确定要删除选中的行吗?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # 默认按钮
            )

            # 如果用户选择了“是”，则执行删除操作
            if confirmation == QMessageBox.Yes:
                # 调用删除函数
                delete_MutiAgentCfg(agent_group_id)

                # 查找对应的工具箱项并删除
                tool_box_item = self.app.toolBox_AgentChat.findChild(QWidget, agent_group_id)
                item_index = self.app.toolBox_AgentChat.indexOf(tool_box_item)

                # 如果找到了该item，则进行删除
                if item_index != -1:
                    self.app.toolBox_AgentChat.removeItem(item_index)

                # 收集需要删除的行索引
                rows_to_delete = [index.row() for index in selected_indexes]
                # 反向删除行以避免索引混乱
                for row in reversed(rows_to_delete):
                    self.model.removeRow(row)

                # 通知视图模型数据已更改
                self.model.layoutChanged.emit()

    def moveSelectedRowsUp(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            if selected_indexes[0].row()==0:
                QMessageBox.warning(self, "提示", "不可移出当前类别所在区域")
                return
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            name = self.model.index(selected_indexes[0].row(), 2).data()
            memo = self.model.index(selected_indexes[0].row(), 3).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data

            item_to_move = self.app.toolBox_AgentChat.findChild(QWidget, agent_user_id)

            if item_to_move:
                current_index = self.app.toolBox_AgentChat.indexOf(item_to_move)  # 获取当前索引
                if current_index > 0:  # 确保不是第一个项
                    # 移动项的逻辑
                    self.app.toolBox_AgentChat.removeItem(current_index)  # 移除当前项
                    self.app.toolBox_AgentChat.insertItem(current_index - 1, item_to_move, QIcon('images/agentmulti.png'), f"{name} ({memo})" if memo else name)  # 将项插入到前面的位置

                    print(f"已将 'label_2' 移动到索引: {current_index - 1}")


            rows_to_move = [index.row() for index in selected_indexes]
            for row in rows_to_move:
                if row > 0:
                    self.model.insertRow(row - 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_agent_group_index()

    def moveSelectedRowsDown(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        rows_count = self.model.rowCount()
        if selected_indexes:
            if selected_indexes[0].row()==rows_count-1:
                QMessageBox.warning(self, "提示", "不可移出当前类别所在区域")
                return
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()
            name = self.model.index(selected_indexes[0].row(), 2).data()
            memo = self.model.index(selected_indexes[0].row(), 3).data()
            print("second_column_data:", second_column_data)

            agent_user_id = second_column_data

            item_to_move = self.app.toolBox_AgentChat.findChild(QWidget, agent_user_id)

            if item_to_move:
                current_index = self.app.toolBox_AgentChat.indexOf(item_to_move)  # 获取当前索引
                if current_index < 1000:  # 确保不是第一个项
                    # 移动项的逻辑
                    self.app.toolBox_AgentChat.removeItem(current_index)  # 移除当前项
                    self.app.toolBox_AgentChat.insertItem(current_index + 1, item_to_move, QIcon('images/agentmulti.png'), f"{name} ({memo})" if memo else name)  # 将项插入到前面的位置

                    print(f"已将 'label_2' 移动到索引: {current_index + 1}")


            rows_to_move = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_move):
                if row < self.model.rowCount() - 1:
                    self.model.insertRow(row + 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()
            self.update_agent_group_index()


    def update_agent_group_index(self):
        for row in range(self.model.rowCount()):
            agent_group_id = self.model.index(row, 1).data()
            update_MutiAgentCfg_by_group_id(agent_group_id,position=row)



    def on_item_double_clicked(self):
        self.open_agent_cfg()


    def open_agent_cfg(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            column =2
            second_column_data = self.model.index(selected_indexes[0].row(), 1).data()

            print("second_column_data:",second_column_data)

            group_id=second_column_data

            agent_group_cfg = query_MutiAgentCfg(group_id=group_id)


            agentmulticonfigdlg = AgentMutiConfigDialog(self.app, agent_group_cfg)

            if agentmulticonfigdlg.exec_() == QDialog.Accepted:

                self.model.setItem(row, column, QStandardItem(agentmulticonfigdlg.name))
                self.model.setItem(row, column+1, QStandardItem(agentmulticonfigdlg.memo))
                self.model.setItem(row, column+2, QStandardItem(",".join([query_AgentCfg(user_id=agent).name for agent in agentmulticonfigdlg.agents.split(",")])))
                self.model.setItem(row, column+3, QStandardItem(query_AgentCfg(user_id=agentmulticonfigdlg.agentcommander).name))


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

    # 修改后的 on_item_changed 方法
    def on_item_changed(self, item):
        if item.isCheckable():
            print(item.checkState())
            print(item.row())
            print(self.model.index(item.row(), 1).data())

            if item.checkState()== Qt.Unchecked:
                group_id = self.model.index(item.row(), 1).data()
                item_to_move = self.app.toolBox_AgentChat.findChild(QWidget, group_id)
                object_name = item_to_move.objectName()
                print(f"The object name of the item is: {object_name}")
                current_index = self.app.toolBox_AgentChat.indexOf(item_to_move)  # 获取当前索引
                # 移动项的逻辑
                self.app.toolBox_AgentChat.removeItem(current_index)  # 移除当前项
                item_to_move.deleteLater()
                del item_to_move
                update_MutiAgentCfg_by_group_id(group_id, is_show=False)
            else:
                group_id = self.model.index(item.row(), 1).data()
                update_MutiAgentCfg_by_group_id(group_id, is_show=True)
                agent =  query_MutiAgentCfg(group_id=group_id)
                self.app.createToolBoxUnit_MutiAgentChat(agent, self.app.toolBox_AgentChat.count())


            self.reorder_rows()




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
