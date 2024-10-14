from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction, QAbstractItemView, QDialogButtonBox, QMessageBox, QCheckBox


class FreezeTableDialog(QDialog):
    def __init__(self, model):
        super(FreezeTableDialog, self).__init__()
        self.model = model
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
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)

        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("日志列表")
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
                    self.model.insertRow(row - 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()

    def moveSelectedRowsDown(self):
        selected_indexes = self.tableView.selectionModel().selectedRows()
        if selected_indexes:
            rows_to_move = [index.row() for index in selected_indexes]
            for row in reversed(rows_to_move):
                if row < self.model.rowCount() - 1:
                    self.model.insertRow(row + 1, self.model.takeRow(row))
            self.model.layoutChanged.emit()


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
