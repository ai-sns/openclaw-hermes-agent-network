from PyQt5.QtCore import QFile, QFileInfo, Qt, pyqtSlot
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMenu, QTableView, QVBoxLayout, QAction, QAbstractItemView, QDialogButtonBox, QMessageBox, QWidget, QHBoxLayout, QLabel, QSlider


class SliderWidget(QWidget):
    def __init__(self, min_value=1, max_value=100, initial_value=50, parent=None):
        super(SliderWidget, self).__init__(parent)
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(min_value, max_value)
        self.slider.setValue(initial_value)
        self.label = QLabel(str(initial_value), self)

        self.slider.valueChanged.connect(self.update_label)

        layout = QHBoxLayout()
        layout.addWidget(self.slider)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_label(self, value):
        self.label.setText(str(value))

    def get_value(self):
        return self.slider.value()


class FreezeTableDialog(QDialog):
    def __init__(self, model):
        super(FreezeTableDialog, self).__init__()
        self.model = model
        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(1, True)
        self.tableView.setColumnWidth(0, 200)  # 设置这一列否则第二列长度过长
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)

        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setWindowTitle("请选择插件")
        self.setWindowIcon(QIcon("images/aisns.png"))
        self.resize(560, 680)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)

    def accept_close(self):
        selected_data = []
        for row in range(self.model.rowCount()):
            slider_widget = self.tableView.indexWidget(self.model.index(row, 0))
            if slider_widget:
                slider_value = slider_widget.get_value()
                second_column_data = self.model.index(row, 1).data()
                pluginfullname = self.model.index(row, 2).data() + ": " + self.model.index(row, 4).data()
                aliasname = self.model.index(row, 3).data()
                selected_data.append((slider_value, second_column_data, pluginfullname, aliasname))

        if not selected_data:
            QMessageBox.warning(self, "No Selection", "Please select at least one row.")
            return

        print('OK, I accept')
        print('Selected Data::', selected_data)
        self.accept()

    def reject_close(self):
        print("reject")
        self.reject()

    def showContextMenu(self, pos):
        selected_rows = self.tableView.selectionModel().selectedRows()
        if selected_rows:
            menu = QMenu(self)
            actions = [("删除", self.deleteSelectedRows), ("上移", self.moveSelectedRowsUp), ("下移", self.moveSelectedRowsDown)]
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
        return [s.strip() for s in s.split(splitter)]

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
                # Create a slider in the first column
                slider_widget = SliderWidget()
                item = QStandardItem()
                model.setItem(row, 0, item)
                for col, field in enumerate(fields):
                    newItem = QStandardItem(field)
                    newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)
                    model.setItem(row, col + 1, newItem)
                row += 1
        file.close()

    dialog = FreezeTableDialog(model)
    for row in range(model.rowCount()):
        slider_widget = SliderWidget()
        dialog.tableView.setIndexWidget(model.index(row, 0), slider_widget)

    dialog.exec_()


if __name__ == '__main__':
    import sys

    main(sys.argv)
