import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QHeaderView, QHBoxLayout, QCheckBox
)
from PyQt5.QtCore import Qt
from db.DBFactory import query_function_mng_all,delete_function_mng
from code_editor import CodeEditor
from pytalk.workflow_design import WorkFlowDesign


class FunctionManager(QWidget):
    def __init__(self,type_str=""):
        # type_str:"0","1","2"
        super().__init__()
        self.type_str=type_str
        print("type_str:",type_str)
        if type_str:
            self.records = query_function_mng_all(function_type=type_str)
        else:
            self.records = query_function_mng_all()

        # 设置窗口标题和大小
        self.setWindowTitle("文件列表管理器")
        self.setGeometry(100, 100, 800, 400)

        # 创建布局和控件
        self.layout = QVBoxLayout()
        self.file_table = QTableWidget(0, 5)  # 创建一个5列的表格

        # 设置列标签
        self.file_table.setHorizontalHeaderLabels(["选择", "函数名称","文件名", "编辑时间","简介"])

        # 设置标题背景颜色
        # self.file_table.horizontalHeader().setStyleSheet("QHeaderView::section {background-color: #c0c0c0;}")

        # 设置选择行为为选中整行
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        # 设置表格不可编辑
        self.file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 连接双击事件
        self.file_table.itemDoubleClicked.connect(self.open_file)

        # 启用排序--不能放在这里，影响增加文件之后的顺序
        # self.file_table.setSortingEnabled(True)

        # 创建按钮布局，用于放置全选复选框和操作按钮
        button_layout = QHBoxLayout()

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)

        self.add_button = QPushButton("新增")
        self.delete_button = QPushButton("删除")
        self.reload_button = QPushButton("刷新")
        self.add_button.clicked.connect(self.add_file)
        self.delete_button.clicked.connect(self.delete_file)
        self.reload_button.clicked.connect(self.reload)

        # 将控件添加到按钮布局中
        button_layout.addWidget(self.select_all_checkbox)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.reload_button)

        # 将控件添加到布局中
        self.layout.addWidget(self.file_table)
        self.layout.addLayout(button_layout)

        # 设置主窗口的布局
        self.setLayout(self.layout)

        # 使表格铺满窗口
        self.file_table.horizontalHeader().setStretchLastSection(True)
        # self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 允许用户手动调整列宽
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.adjust_column_widths()
        self.add_records()
        self.code_editor = None

    def reload(self):
        # 使用 clearContents() 方法清空所有单元格的内容
        self.file_table.clearContents()

        # 使用 setRowCount(0) 方法设置行数为 0，删除所有行
        self.file_table.setRowCount(0)

        type_str=self.type_str
        if type_str:
            self.records = query_function_mng_all(function_type=type_str)
        else:
            self.records = query_function_mng_all()



        self.add_records()


    def adjust_column_widths(self):
        """调整列宽，确保列宽为整数"""
        total_width = self.file_table.viewport().width()
        if total_width <= 0:
            return

        # 设置列宽，确保使用整数
        self.file_table.setColumnWidth(0, 50)  # 选择列宽
        self.file_table.setColumnWidth(1, int(total_width * 0.4))  # 标题列宽
        self.file_table.setColumnWidth(2, int(total_width * 0.2))  # 说明列宽
        self.file_table.setColumnWidth(3, int(total_width * 0.2))  # 类型列宽

        self.file_table.setColumnWidth(4, int(total_width * 0.2))  # 编辑时间列宽
        # self.file_table.setColumnWidth(5, 0)  # 编辑时间列宽

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
            item.setText(record.name)
            # 将数据值设置为单元格的内部数据
            item.setData(Qt.UserRole, record.function_id)  # 使用 Qt.UserRole 存储自定义数据
            # 设置单元格的项

            self.file_table.setItem(row_position, 1, item)  # 标题
            self.file_table.setItem(row_position, 2, QTableWidgetItem(record.file_path))  # 说明
            self.file_table.setItem(row_position, 3, QTableWidgetItem(str(record.create_time)))  # 类型
            self.file_table.setItem(row_position, 4, QTableWidgetItem(str(record.description)))  # 编辑时间

        self.file_table.setSortingEnabled(True)

    def toggle_select_all(self, state):
        """全选或全不选复选框的状态改变时执行"""
        for row in range(self.file_table.rowCount()):
            checkbox_item = self.file_table.item(row, 0)
            checkbox_item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

    def add_file(self):

        if self.code_editor:
            fun_dialog = self.code_editor
        else:
            fun_dialog = CodeEditor(self)
            fun_dialog.create_widget()
            fun_dialog.setObjectName("codeeditor")
            self.code_editor = fun_dialog
        fun_dialog.function_id=""
        fun_dialog.loadFile()

        fun_dialog.setObjectName("codeeditor")
        self.parent().addWidget(fun_dialog)
        self.parent().setCurrentWidget(fun_dialog)


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
                function_id = item.data(Qt.UserRole)  # 使用 Qt.UserRole 获取数据

            delete_function_mng(function_id=function_id)

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
            function_name = item.text()
            # 获取数据值
            function_id = item.data(Qt.UserRole)  # 使用 Qt.UserRole 获取数据

        print("function_name", function_name)
        print("function_id",function_id)
        # os.startfile(file_path)  # 在 Windows 上打开文件
        # 创建代码编辑器窗口并设置初始内容

        if self.code_editor:
            fun_dialog = self.code_editor
        else:
            fun_dialog = CodeEditor(self)
            fun_dialog.create_widget()
            fun_dialog.setObjectName("codeeditor")
            self.code_editor = fun_dialog
        fun_dialog.function_id=function_id
        fun_dialog.loadFile()
        self.parent().addWidget(fun_dialog)
        self.parent().setCurrentWidget(fun_dialog)



    def open_filebak(self, item=None):
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
    file_manager = FunctionManager()
    file_manager.show()
    sys.exit(app.exec_())
