import sys
import os
import datetime

from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QHeaderView, QCheckBox, QHBoxLayout, QLineEdit, QFormLayout, QLabel, QDialog, QTextEdit
)
from PyQt5.QtCore import Qt
from workflow_design import WorkFlowDesign
from db.DBFactory import query_task_schedule_all, delete_task_schedule, copy_workflow, query_task_schedule
from util import generate_random_id

class DataRecordDialog(QDialog):
    """对话框，用于展示单条记录"""
    def __init__(self,data):
        super().__init__()
        self.setWindowTitle("数据记录")
        # self.setGeometry(100, 100, 400, 300)
        self.resize(500, 400)  # 设置对话框的初始大小

        # 使用 QFormLayout 布局来展示记录
        layout = QFormLayout()

        # 将记录的每个字段添加到布局中
        layout.addRow(QLabel("ID:"), QLabel(str(data.id)))

        title_label = QLabel(data.title)
        title_label.setWordWrap(True)  # 启用自动折行
        layout.addRow(QLabel("标题:"), title_label)


        description_label = QLabel(data.description)
        description_label.setWordWrap(True)  # 启用自动折行
        layout.addRow(QLabel("描述:"), description_label)

        layout.addRow(QLabel("任务类型:"), QLabel(data.task_type))

        # 使用 QTextEdit 来显示描述内容
        parameter_text_edit = QTextEdit()
        parameter_text_edit.setPlainText(data.parameter)
        parameter_text_edit.setReadOnly(True)  # 设置为只读
        parameter_text_edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # 设置自动换行
        layout.addRow(QLabel("参数:"), parameter_text_edit)


        layout.addRow(QLabel("预定运行时间:"), QLabel(data.schedule_time.strftime("%Y-%m-%d %H:%M:%S") if data.schedule_time is not None else ""))
        layout.addRow(QLabel("实际运行时间:"), QLabel(data.run_time.strftime("%Y-%m-%d %H:%M:%S") if data.run_time is not None else ""))
        layout.addRow(QLabel("运行结果:"), QLabel(data.run_result).setWordWrap(True))
        # 根据 data.status 的值动态设置 QLabel 显示的文本
        layout.addRow(QLabel("状态:"), QLabel("未开始" if data.status == 0 else "运行成功" if data.status == 1 else "运行失败" if data.status == 2 else "未知状态"))

        # 添加按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        # 连接按钮的点击信号
        ok_button.clicked.connect(self.accept)  # 点击确定，关闭对话框并返回 OK
        cancel_button.clicked.connect(self.reject)  # 点击取消，关闭对话框并返回 Cancel

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        # 将按钮布局添加到主布局中
        layout.addRow(button_layout)

        self.setLayout(layout)
class TaskSchedule(QWidget):
    def __init__(self, task_type=""):
        super().__init__()
        self.task_type = task_type
        if task_type:
            self.records = query_task_schedule_all(task_type=task_type)
        else:
            self.records = query_task_schedule_all()

        self.setWindowTitle("任务运行管理")
        self.setGeometry(100, 100, 800, 400)

        # 创建布局和控件
        self.layout = QVBoxLayout()
        self.file_table = QTableWidget(0, 7)  # 创建一个5列的表格，包括复选框和隐藏列

        # 设置列标签
        self.file_table.setHorizontalHeaderLabels(["选择", "标题", "说明", "类型", "状态", "预计运行", "实际运行"])

        # 设置选择行为为选中整行
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        # 设置表格不可编辑
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 连接双击事件
        self.file_table.itemDoubleClicked.connect(self.open_file)



        # 创建按钮布局，用于放置全选复选框和操作按钮
        button_layout = QHBoxLayout()

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)

        # 创建 QLineEdit 实例，用于输入搜索关键词
        self.searchLineEdit = QLineEdit(self)
        #"Search in Title..."
        self.searchLineEdit.setPlaceholderText("搜索...")
        self.searchLineEdit.setFixedWidth(400)  # 设置固定宽度为150像素
        # 或者使用最小宽度
        #self.searchLineEdit.setMinimumWidth(100)  # 设置最小宽度为100像素
        self.searchLineEdit.textChanged.connect(self.filterTable)


        self.delete_button = QPushButton("删除")
        self.reload_button = QPushButton("刷新")

        self.delete_button.clicked.connect(self.delete_file)
        self.reload_button.clicked.connect(self.reload)

        # 将控件添加到按钮布局中
        button_layout.addWidget(self.select_all_checkbox)
        button_layout.addWidget(self.searchLineEdit)

        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.reload_button)


        # 将控件添加到主布局中
        self.layout.addWidget(self.file_table)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

        # 使表格铺满窗口
        self.file_table.horizontalHeader().setStretchLastSection(True)
        # self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 允许用户手动调整列宽
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 调整列宽
        self.adjust_column_widths()
        self.add_records()

    def reload(self):
        # 使用 clearContents() 方法清空所有单元格的内容
        self.file_table.clearContents()

        # 使用 setRowCount(0) 方法设置行数为 0，删除所有行
        self.file_table.setRowCount(0)

        task_type = self.task_type
        if task_type:
            self.records = query_task_schedule_all(task_type=task_type)
        else:
            self.records = query_task_schedule_all()

        self.add_records()


    def adjust_column_widths(self):
        """调整列宽，确保列宽为整数"""
        total_width = self.file_table.viewport().width()
        if total_width <= 0:
            return

        # 设置列宽，确保使用整数
        self.file_table.setColumnWidth(0, 50)  # 选择列宽
        self.file_table.setColumnWidth(1, int(total_width * 0.3))  # 标题列宽
        self.file_table.setColumnWidth(2, int(total_width * 0.2))  # 说明列宽
        self.file_table.setColumnWidth(3, int(total_width * 0.1))  # 类型列宽
        self.file_table.setColumnWidth(4, int(total_width * 0.1))  # 状态列宽
        self.file_table.setColumnWidth(5, int(total_width * 0.15))  # 预定运行列宽
        self.file_table.setColumnWidth(6, int(total_width * 0.15))  # 实际运行列宽



    def add_records(self):
        """新增记录并将其添加到表格中"""
        self.file_table.setSortingEnabled(False)
        for record in self.records:
            row_position = self.file_table.rowCount()
            self.file_table.insertRow(row_position)

            # 在第一列添加复选框
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.file_table.setItem(row_position, 0, checkbox_item)

            # 创建 QTableWidgetItem 实例
            item = QTableWidgetItem()
            # 将文本值设置为单元格显示的内容
            item.setText(record.title)
            # 将数据值设置为单元格的内部数据
            item.setData(Qt.UserRole, record.task_id)  # 使用 Qt.UserRole 存储自定义数据
            # 设置单元格的项

            self.file_table.setItem(row_position, 1, item)  # 标题
            self.file_table.setItem(row_position, 2, QTableWidgetItem(record.description))  # 说明
            self.file_table.setItem(row_position, 3, QTableWidgetItem(record.task_type))  # 类型
            self.file_table.setItem(row_position, 4, QTableWidgetItem(record.status))  # 状态
            self.file_table.setItem(row_position, 5, QTableWidgetItem(str(record.create_time)))  # 编辑时间
            self.file_table.setItem(row_position, 6, QTableWidgetItem(str(record.create_time)))  # 编辑时间

        self.file_table.setSortingEnabled(True)

    def toggle_select_all(self, state):
        """全选或全不选复选框的状态改变时执行"""
        for row in range(self.file_table.rowCount()):
            checkbox_item = self.file_table.item(row, 0)
            checkbox_item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

    def filterTable(self, text):
        # 根据输入框的内容过滤表格项的标题列
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 1)  # 获取标题列的单元格
            if item:
                self.file_table.setRowHidden(row, text not in item.text())




    def delete_file(self):
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

            item = self.file_table.item(row, 1)
            if item:
                task_id = item.data(Qt.UserRole)  # 使用 Qt.UserRole 获取数据

            delete_task_schedule(task_id=task_id)

            self.file_table.removeRow(row)

        self.reload()

    def open_file(self, item=None):
        """打开所选文件"""
        if item is None:
            selected_items = self.file_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选择一个文件进行打开。")
                return
            item = selected_items[0]

        row = self.file_table.row(item)
        title = self.file_table.item(row, 1).text()  # 获取文件路径
        item = self.file_table.item(row, 1)
        if item:
            # 获取文本值
            # title = item.text()
            # 获取数据值
            task_id = item.data(Qt.UserRole)  # 使用 Qt.UserRole 获取数据

        print("task_id",task_id)
        # os.startfile(file_path)  # 在 Windows 上打开文件
        record = query_task_schedule(task_id=task_id)
        dialog = DataRecordDialog(record)
        dialog.exec_()

    def get_file_info(self, file_path):
        """获取文件的详细信息"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)  # 获取文件大小
            file_name = os.path.splitext(file_name)[0]  # 获取文件类型
            modified_time = os.path.getmtime(file_path)  # 获取最后编辑时间
            modified_time_str = datetime.datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"无法获取文件信息: {file_path}, 错误: {e}")
            file_size = "N/A"
            file_type = "N/A"
            modified_time_str = "N/A"

        # 返回文件信息的列表
        return [file_name, f"{file_size}", modified_time_str, file_path]


