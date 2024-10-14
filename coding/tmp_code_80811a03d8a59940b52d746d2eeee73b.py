import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt


class FileManager(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("文件列表管理器")
        self.setGeometry(100, 100, 800, 400)

        # 创建布局和控件
        self.layout = QVBoxLayout()
        self.file_table = QTableWidget(0, 4)  # 创建一个4列的表格

        # 设置列标签
        self.file_table.setHorizontalHeaderLabels(["文件路径", "文件大小", "文件类型", "最后编辑时间"])

        # 设置选择行为为选中整行
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        # 设置表格不可编辑
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 连接双击事件
        self.file_table.itemDoubleClicked.connect(self.open_file)

        # 创建按钮
        self.add_file_button = QPushButton("新增文件")
        self.add_directory_button = QPushButton("新增目录")
        self.delete_button = QPushButton("删除文件")

        # 连接按钮的点击事件
        self.add_file_button.clicked.connect(self.add_file)
        self.add_directory_button.clicked.connect(self.add_directory)  # 连接新增目录的事件
        self.delete_button.clicked.connect(self.delete_file)

        # 将控件添加到布局中
        self.layout.addWidget(self.file_table)
        self.layout.addWidget(self.add_file_button)
        self.layout.addWidget(self.add_directory_button)  # 添加目录按钮
        self.layout.addWidget(self.delete_button)

        # 设置主窗口的布局
        self.setLayout(self.layout)

        # 使表格铺满窗口
        self.file_table.horizontalHeader().setStretchLastSection(True)
        # 允许用户手动调整列宽
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 根据窗口宽度设置列宽
        self.adjust_column_widths()

    def adjust_column_widths(self):
        """调整表格列宽"""
        total_width = self.file_table.viewport().width()  # 获取当前视口的宽度
        if total_width <= 0:  # 如果宽度为0，返回
            return

        column_widths = [0.6, 0.1, 0.1, 0.2]  # 每列所占比例
        for i, width_ratio in enumerate(column_widths):
            column_width = int(total_width * width_ratio)  # 计算列的宽度
            self.file_table.setColumnWidth(i, column_width)  # 设置列宽

    def add_file(self):
        """新增文件并将其添加到表格中"""
        self.file_table.setSortingEnabled(False)
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "所有文件 (*)", options=options)

        for file in files:
            file_info = self.get_file_info(file)
            row_position = self.file_table.rowCount()
            self.file_table.insertRow(row_position)
            self.file_table.setItem(row_position, 0, QTableWidgetItem(file_info[0]))
            self.file_table.setItem(row_position, 1, QTableWidgetItem(file_info[1]))
            self.file_table.setItem(row_position, 2, QTableWidgetItem(file_info[2]))
            self.file_table.setItem(row_position, 3, QTableWidgetItem(file_info[3]))

        self.file_table.setSortingEnabled(True)

    def add_directory(self):
        """新增目录并将其所有文件添加到表格中"""
        self.file_table.setSortingEnabled(False)
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(self, "选择目录", options=options)

        if directory:  # 如果用户选择了目录
            # 遍历目录中的所有文件
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)  # 获取文件完整路径
                    file_info = self.get_file_info(file_path)
                    row_position = self.file_table.rowCount()
                    self.file_table.insertRow(row_position)
                    self.file_table.setItem(row_position, 0, QTableWidgetItem(file_info[0]))
                    self.file_table.setItem(row_position, 1, QTableWidgetItem(file_info[1]))
                    self.file_table.setItem(row_position, 2, QTableWidgetItem(file_info[2]))
                    self.file_table.setItem(row_position, 3, QTableWidgetItem(file_info[3]))

        self.file_table.setSortingEnabled(True)

    def delete_file(self):
        """删除所选文件"""
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件进行删除。")
            return
        
        for item in selected_items:
            row = self.file_table.row(item)
            self.file_table.removeRow(row)

    def open_file(self, item=None):
        """打开所选文件"""
        if item is None:
            selected_items = self.file_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选择一个文件进行打开。")
                return
            item = selected_items[0]

        row = self.file_table.row(item)
        file_path = self.file_table.item(row, 0).text()  # 获取文件路径
        os.startfile(file_path)  # 在 Windows 上打开文件

    def get_file_info(self, file_path):
        """获取文件的详细信息"""
        try:
            file_size = os.path.getsize(file_path)  # 获取文件大小
            file_type = os.path.splitext(file_path)[1]  # 获取文件类型
            modified_time = os.path.getmtime(file_path)  # 获取最后编辑时间
            modified_time_str = datetime.datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # 如果发生异常，提供默认值
            print(f"无法获取文件信息: {file_path}, 错误: {e}")
            file_size = "N/A"
            file_type = "N/A"
            modified_time_str = "N/A"

        # 返回文件信息的列表
        return [file_path, f"{file_size}", file_type, modified_time_str]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_manager = FileManager()
    file_manager.show()
    sys.exit(app.exec_())