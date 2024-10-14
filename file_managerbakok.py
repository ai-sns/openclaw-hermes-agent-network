import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QHeaderView, QHBoxLayout
)
from PyQt5.QtCore import Qt


class FileManager(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("文件列表管理器")
        self.setGeometry(100, 100, 800, 400)

        # 创建主布局
        self.layout = QVBoxLayout()

        # 创建文件表格
        self.file_table = QTableWidget(0, 5)  # 创建一个5列的表格
        self.file_table.setHorizontalHeaderLabels(["文件名称", "大小", "类型", "编辑时间", "路径"])
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)  # 设置选择行为为选中整行
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 设置表格不可编辑
        self.file_table.itemDoubleClicked.connect(self.open_file)  # 连接双击事件

        # 创建按钮
        # self.add_file_button = QPushButton("新增文件")
        self.open_file_button = QPushButton("打开文件")
        self.delete_button = QPushButton("删除文件")

        # 连接按钮的点击事件
        # self.add_file_button.clicked.connect(self.add_file)
        self.open_file_button.clicked.connect(self.open_file_btn)
        self.delete_button.clicked.connect(self.delete_file)

        # 创建一个水平布局用于放置按钮
        button_layout = QHBoxLayout()
        # button_layout.addWidget(self.add_file_button)
        button_layout.addWidget(self.open_file_button)
        button_layout.addWidget(self.delete_button)

        # 将控件添加到主布局中
        self.layout.addWidget(self.file_table)  # 添加文件表格
        self.layout.addLayout(button_layout)  # 添加按钮布局

        # 设置主窗口的布局
        self.setLayout(self.layout)

        # 使表格铺满窗口
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 根据窗口宽度设置列宽
        self.adjust_column_widths()

    def showEvent(self, event):
        """窗口显示事件"""
        # 使用 clearContents() 方法清空所有单元格的内容
        self.file_table.clearContents()

        # 使用 setRowCount(0) 方法设置行数为 0，删除所有行
        self.file_table.setRowCount(0)
        self.add_directory()  # 打开窗口时自动添加目录
        super().showEvent(event)

    def adjust_column_widths(self):
        """调整表格列宽"""
        total_width = self.file_table.viewport().width()  # 获取当前视口的宽度
        if total_width <= 0:  # 如果宽度为0，返回
            return

        column_widths = [0.2, 0.1, 0.1, 0.1, 0.5]  # 每列所占比例
        for i, width_ratio in enumerate(column_widths):
            column_width = int(total_width * width_ratio)  # 计算列的宽度
            self.file_table.setColumnWidth(i, column_width)  # 设置列宽

    def add_file(self):
        """新增文件并将其添加到表格中"""
        self.file_table.setSortingEnabled(False)  # 禁止排序，避免添加文件时排序影响位置
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
            self.file_table.setItem(row_position, 4, QTableWidgetItem(file_info[4]))

        self.file_table.setSortingEnabled(True)  # 恢复排序

    def add_directory(self):
        """新增目录并将其所有文件添加到表格中"""
        taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
        task_id = taskpage.task_id  # 获取任务ID
        directory_path = os.path.join('resource', 'attachment', 'chat', task_id)  # 构造目录路径
        self.file_table.setSortingEnabled(False)  # 禁止排序
        directory = directory_path  # 直接使用构造的目录路径

        if directory:  # 如果用户选择了目录
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
                    self.file_table.setItem(row_position, 4, QTableWidgetItem(file_info[4]))

        self.file_table.setSortingEnabled(True)  # 恢复排序

    def delete_file(self):
        """删除所选文件"""
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件进行删除。")
            return

            # 弹出确认对话框，询问用户是否确认删除
        reply = QMessageBox.question(self, "确认删除", "您确定要删除所选文件吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        # 如果用户选择否，取消删除操作
        if reply == QMessageBox.No:
            return

        # 获取被选中行的行号，使用set来避免重复
        rows_to_delete = set(self.file_table.row(item) for item in selected_items)

        # 从高到低删除行
        for row in sorted(rows_to_delete, reverse=True):
            file_path=self.file_table.item(row, 4).text()
            file_path = os.path.join(os.getcwd(), file_path)
            print("deleting..:",file_path)
            try:
                # 检查文件是否存在
                if os.path.isfile(file_path):
                    os.remove(file_path)  # 删除文件
                    print(f"文件 '{file_path}' 已成功删除。")
                else:
                    print(f"文件 '{file_path}' 不存在。")
            except Exception as e:
                print(f"删除文件时发生错误: {e}")

            self.file_table.removeRow(row)  # 删除所选行，必须放后面不让会删除错误

    def delete_filebak(self):
        """删除所选文件"""
        selected_rows = [row for row in range(self.file_table.rowCount()) if self.file_table.item(row, 0).checkState() == Qt.Checked]
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个文件进行删除。")
            return

        # 弹出确认对话框，询问用户是否确认删除
        reply = QMessageBox.question(self, "确认删除", "您确定要删除所选文件吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # 如果用户选择否，取消删除操作
        if reply == QMessageBox.No:
            return

        for row in reversed(selected_rows):  # 从最后一行开始删除，以避免索引错误

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
        file_name =  self.file_table.item(row, 0).text()
        file_path = self.file_table.item(row, 4).text()  # 获取文件路径
        file_type =  self.file_table.item(row, 2).text()  # 获取文件路径



        if file_type==".py" or file_type==".js" or file_type==".html" or file_type==".htm":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("python",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "编辑器":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环


        elif file_type==".mermaid":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("mermaid",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "Mermaid":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        elif file_type==".mindmap":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("mindmap",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "MindMap":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        else:
            os.startfile(file_path)  # 在 Windows 上打开文件


    def open_file_btn(self):

        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件进行打开。")
            return
        item = selected_items[0]

        row = self.file_table.row(item)
        file_name = self.file_table.item(row, 0).text()
        file_path = self.file_table.item(row, 4).text()  # 获取文件路径
        file_type = self.file_table.item(row, 2).text()  # 获取文件路径
        if file_type==".py" or file_type==".js" or file_type==".html" or file_type==".htm":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("python",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "编辑器":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环


        elif file_type==".mermaid":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("mermaid",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "Mermaid":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        elif file_type==".mindmap":
            with open(file_path, "rt", encoding='utf-8') as file:
                text=file.read()
            taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
            taskpage.edit_selected_content("mindmap",text,file_name)
            tabs = self.parent().parent()
            for index in range(tabs.count()):
                if tabs.tabText(index) == "MindMap":
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环

        else:
            os.startfile(file_path)  # 在 Windows 上打开文件

    def get_file_info(self, file_path):
        """获取文件的详细信息"""
        try:
            file_name = os.path.basename(file_path)  # 获取文件名部分
            file_size = os.path.getsize(file_path)  # 获取文件大小
            file_type = os.path.splitext(file_path)[1]  # 获取文件类型
            modified_time = os.path.getmtime(file_path)  # 获取最后编辑时间
            modified_time_str = datetime.datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"无法获取文件信息: {file_path}, 错误: {e}")  # 捕获异常并输出错误信息
            file_name = "N/A"
            file_size = "N/A"
            file_type = "N/A"
            modified_time_str = "N/A"

        return [file_name, f"{file_size:,}", file_type, modified_time_str, file_path]  # 返回文件信息列表


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_manager = FileManager()
    file_manager.show()
    sys.exit(app.exec_())
