import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QDialog,
    QTableView,
    QHeaderView,
    QWidget,
    QSlider,
    QLabel,
    QHBoxLayout,
    QDialogButtonBox,
    QAbstractItemView,
    QMessageBox,
    QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from db.DBFactory import Session, ModelMetrics
from llmrecodialog import EvalApp

session = Session()

# Add some initial data if the database is empty
if not session.query(ModelMetrics).first():
    initial_data = ModelMetrics(connector_name="Connector1", model_name="Model1", price=100, speed=50, understanding=60,
                                summarizing=70, knowledge=80, logical_reasoning=90, math=50, coding=60, writing=70,
                                attachment=80, image_recognition=90, image_generation=50, video_generation=60,
                                video_recognition=70, searching=80, tool_ability="Tool1")
    session.add(initial_data)
    session.commit()


class SliderWidget(QWidget):
    def __init__(self, min_value=0, max_value=100, initial_value=50, parent=None):
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

    def set_value(self, value):
        self.slider.setValue(value)


class ModelEvaluationDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("模型评测")

        screen = QApplication.primaryScreen().availableGeometry()
        screen_width = screen.width()
        screen_height = int(screen.height() * 0.95)  # 高度减少20%，并转换为整数

        self.resize(screen_width, screen_height)

        self.model = QStandardItemModel(0, 18)
        self.model.setHorizontalHeaderLabels([
            "连接器名称", "模型名称", "价格", "速度", "理解能力", "总结能力", "知识面", "逻辑推理", "数学计算",
            "代码编程", "创作写作文档", "附件能力", "图文识别能力", "图片生成能力", "视频生成能力", "视频识别能力", "搜索能力", "工具能力"
        ])

        self.tableView = QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setEditTriggers(QAbstractItemView.DoubleClicked)

        layout = QVBoxLayout()
        layout.addWidget(self.tableView)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加新记录")
        self.add_button.clicked.connect(self.add_record)
        button_layout.addWidget(self.add_button)

        # button_layout = QHBoxLayout()
        self.edit_button = QPushButton("编辑记录")
        self.edit_button.clicked.connect(self.edit_record)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("删除记录")
        self.delete_button.clicked.connect(self.delete_record)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("确定")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        self.load_data()

        # 窗口尺寸变化时调整列宽
        # self.tableView.horizontalHeader().sectionResized.connect(self.adjust_column_widths)
        # self.tableView.horizontalScrollBar().rangeChanged.connect(self.adjust_column_widths)
        self.adjust_column_widths()

    def load_data(self, datas=None):
        self.model.removeRows(0, self.model.rowCount())
        if datas is None:
            metrics = session.query(ModelMetrics).all()
        for metric in metrics:
            row = [
                QStandardItem(metric.connector_name),
                QStandardItem(metric.model_name),
                QStandardItem(str(metric.price)),
                QStandardItem(),  # speed slider will be added here
                QStandardItem(),  # understanding slider will be added here
                QStandardItem(),  # summarizing slider will be added here
                QStandardItem(),  # knowledge slider will be added here
                QStandardItem(),  # logical_reasoning slider will be added here
                QStandardItem(),  # math slider will be added here
                QStandardItem(),  # coding slider will be added here
                QStandardItem(),  # writing slider will be added here
                QStandardItem(),  # attachment slider will be added here
                QStandardItem(),  # image_recognition slider will be added here
                QStandardItem(),  # image_generation slider will be added here
                QStandardItem(),  # video_generation slider will be added here
                QStandardItem(),  # video_recognition slider will be added here
                QStandardItem(),  # searching slider will be added here
                QStandardItem(metric.tool_ability),
            ]
            self.model.appendRow(row)
            # Add sliders to the respective columns
            self.add_sliders_to_row(self.model.rowCount() - 1, metric)

        self.adjust_column_widths()

    def add_sliders_to_row(self, row_index, metric):
        slider_columns = {
            3: metric.speed if metric else 0,
            4: metric.understanding if metric else 0,
            5: metric.summarizing if metric else 0,
            6: metric.knowledge if metric else 0,
            7: metric.logical_reasoning if metric else 0,
            8: metric.math if metric else 0,
            9: metric.coding if metric else 0,
            10: metric.writing if metric else 0,
            11: metric.attachment if metric else 0,
            12: metric.image_recognition if metric else 0,
            13: metric.image_generation if metric else 0,
            14: metric.video_generation if metric else 0,
            15: metric.video_recognition if metric else 0,
            16: metric.searching if metric else 0,
        }
        for col, value in slider_columns.items():
            slider_widget = SliderWidget(initial_value=value)
            self.tableView.setIndexWidget(self.model.index(row_index, col), slider_widget)

    def adjust_column_widths(self):
        # total_width = self.tableView.viewport().width()
        screen = QApplication.primaryScreen().availableGeometry()
        total_width = screen.width()
        column_count = self.model.columnCount()
        column_width = total_width // column_count

        for column in range(column_count):
            self.tableView.setColumnWidth(column, column_width)

    def add_record(self):
        dialog = EvalApp()
        if dialog.exec_():
            result = dialog.get_result()  # 通过get_result方法获取对话框返回的值
            print(result)  # 打印结果
        res_list = result.split(",")
        ls = [l if l != " " else 0 for l in res_list]
        row = [
            QStandardItem(ls[0]),  # connector_name
            QStandardItem(ls[1]),  # model_name7
            QStandardItem(ls[2]),  # price
            QStandardItem(ls[3]),  # speed slider will be added here
            QStandardItem(ls[4]),  # understanding slider will be added here
            QStandardItem(ls[5]),  # summarizing slider will be added here
            QStandardItem(ls[6]),  # knowledge slider will be added here
            QStandardItem(ls[7]),  # logical_reasoning slider will be added here
            QStandardItem(ls[8]),  # math slider will be added here
            QStandardItem(ls[9]),  # coding slider will be added here
            QStandardItem(ls[10]),  # writing slider will be added here
            QStandardItem(ls[11]),  # attachment slider will be added here
            QStandardItem(ls[12]),  # image_recognition slider will be added here
            QStandardItem(ls[13]),  # image_generation slider will be added here
            QStandardItem(ls[14]),  # video_generation slider will be added here
            QStandardItem(ls[15]),  # video_recognition slider will be added here
            QStandardItem(ls[16]),  # searching slider will be added here
            QStandardItem(ls[17]),  # tool_ability
        ]
        self.model.appendRow(row)
        # self.add_sliders_to_row(self.model.rowCount() - 1, row)
        slider_columns = {i: int(ls[i]) for i in range(3, 16 + 1)}
        print(slider_columns)
        # slider_columns = {
        #     3: ls[3],
        #     4: ls[4],
        #     5: ls[5],
        #     6: ls[3],
        #     7: ls[3],
        #     8: ls[3],
        #     9: ls[3],
        #     10: metric.writing if metric else 0,
        #     11: metric.attachment if metric else 0,
        #     12: metric.image_recognition if metric else 0,
        #     13: metric.image_generation if metric else 0,
        #     14: metric.video_generation if metric else 0,
        #     15: metric.video_recognition if metric else 0,
        #     16: metric.searching if metric else 0,
        # }
        for col, value in slider_columns.items():
            slider_widget = SliderWidget(initial_value=value)
            self.tableView.setIndexWidget(self.model.index(self.model.rowCount() - 1, col), slider_widget)
        self.adjust_column_widths()

    def edit_record(self):
        selected = self.tableView.selectionModel().selectedRows()
        if selected:
            for index in selected:
                print("index.row-->", index.row())
                connector_name = self.model.item(index.row(), 0).text()
                model_name = self.model.item(index.row(), 1).text()
                price = float(self.model.item(index.row(), 2).text())
                # metric = session.query(ModelMetrics).filter(
                #     ModelMetrics.connector_name == connector_name,
                #     ModelMetrics.model_name == model_name
                # ).first()
                # inx = self.model.index(index.row(), 3)
                # slider_widget = self.tableView.indexWidget(inx)
                # speed = self.tableView.indexWidget(self.model.index(index.row(), 3)).get_value()
                # 获取 SliderWidget 的值
                # slider_value = slider_widget.value() if slider_widget else None
                # print("slider_widget-->", speed)

                metric = ModelMetrics(
                    connector_name=connector_name,
                    model_name=model_name,
                    price=price,
                    speed=int(self.tableView.indexWidget(self.model.index(index.row(), 3)).get_value()),
                    understanding=int(self.tableView.indexWidget(self.model.index(index.row(),4)).get_value()),
                    summarizing=int(self.tableView.indexWidget(self.model.index(index.row(),5)).get_value()),
                    knowledge=int(self.tableView.indexWidget(self.model.index(index.row(),6)).get_value()),
                    logical_reasoning=int(self.tableView.indexWidget(self.model.index(index.row(),7)).get_value()),
                    math=int(self.tableView.indexWidget(self.model.index(index.row(),8)).get_value()),
                    coding=int(self.tableView.indexWidget(self.model.index(index.row(),9)).get_value()),
                    writing=int(self.tableView.indexWidget(self.model.index(index.row(),10)).get_value()),
                    attachment=int(self.tableView.indexWidget(self.model.index(index.row(),11)).get_value()),
                    image_recognition=int(self.tableView.indexWidget(self.model.index(index.row(),12)).get_value()),
                    image_generation=int(self.tableView.indexWidget(self.model.index(index.row(),13)).get_value()),
                    video_generation=int(self.tableView.indexWidget(self.model.index(index.row(),14)).get_value()),
                    video_recognition=int(self.tableView.indexWidget(self.model.index(index.row(),15)).get_value()),
                    searching=int(self.tableView.indexWidget(self.model.index(index.row(),16)).get_value()),
                    tool_ability=self.model.item(index.row(), 17).text()
                )
                # self.res = metric
                dialog = EvalApp(res=metric)
                if dialog.exec_():
                    res = dialog.get_result()
                    result = res.split(",")  # 通过get_result方法获取对话框返回的值
                    role = Qt.DisplayRole
                    new_values = {
                        0: result[0],
                        1: result[1],
                        2: result[2],
                        3: result[3],
                        4: result[4],
                        5: result[5],
                        6: result[6],
                        7: result[7],
                        8: result[8],
                        9: result[9],
                        10: result[10],
                        11: result[11],
                        12: result[12],
                        13: result[13],
                        14: result[14],
                        15: result[15],
                        16: result[16],
                        17: result[17]
                        # ... 为其他列添加新值
                    }
                    # 遍历所有列
                    for column, new_value in new_values.items():
                        # 设置新值，这里使用Qt.EditRole，也可以根据需要使用Qt.DisplayRole
                        # self.tableView.model().setData(index.sibling(index.row(), column), new_value, Qt.EditRole)

                        if column > 2 and column < 17:
                            slider_widget = SliderWidget(initial_value=int(new_value.strip()))
                            self.tableView.setIndexWidget(self.model.index(self.model.rowCount() - 1, column),
                                                          slider_widget)
                        else:
                            self.model.item(index.row(), column).setText(new_value.strip())
                        self.adjust_column_widths()

                    print(result)  # 打印结果

            # self.adjust_column_widths()
        # row = [
        #     QStandardItem(""),  # connector_name
        #     QStandardItem(""),  # model_name
        #     QStandardItem("0"),  # price
        #     QStandardItem(),  # speed slider will be added here
        #     QStandardItem(),  # understanding slider will be added here
        #     QStandardItem(),  # summarizing slider will be added here
        #     QStandardItem(),  # knowledge slider will be added here
        #     QStandardItem(),  # logical_reasoning slider will be added here
        #     QStandardItem(),  # math slider will be added here
        #     QStandardItem(),  # coding slider will be added here
        #     QStandardItem(),  # writing slider will be added here
        #     QStandardItem(),  # attachment slider will be added here
        #     QStandardItem(),  # image_recognition slider will be added here
        #     QStandardItem(),  # image_generation slider will be added here
        #     QStandardItem(),  # video_generation slider will be added here
        #     QStandardItem(),  # video_recognition slider will be added here
        #     QStandardItem(),  # searching slider will be added here
        #     QStandardItem(""),  # tool_ability
        # ]
        # self.model.appendRow(row)
        # self.add_sliders_to_row(self.model.rowCount() - 1, None)
        # self.adjust_column_widths()

    def delete_record(self):
        selected = self.tableView.selectionModel().selectedRows()
        if selected:
            reply = QMessageBox.question(self, "确认删除", "确定要删除选中的记录吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                for index in selected:
                    connector_name = self.model.item(index.row(), 0).text()
                    model_name = self.model.item(index.row(), 1).text()
                    metric = session.query(ModelMetrics).filter(
                        ModelMetrics.connector_name == connector_name,
                        ModelMetrics.model_name == model_name
                    ).first()
                    if metric:
                        session.delete(metric)
                        session.commit()
                    self.model.removeRow(index.row())
                self.adjust_column_widths()

    def accept(self):
        for row in range(self.model.rowCount()):
            connector_name = self.model.item(row, 0).text()
            model_name = self.model.item(row, 1).text()
            price = float(self.model.item(row, 2).text())
            slider_columns = {
                3: 'speed',
                4: 'understanding',
                5: 'summarizing',
                6: 'knowledge',
                7: 'logical_reasoning',
                8: 'math',
                9: 'coding',
                10: 'writing',
                11: 'attachment',
                12: 'image_recognition',
                13: 'image_generation',
                14: 'video_generation',
                15: 'video_recognition',
                16: 'searching',
            }
            sliders = {}
            for col in slider_columns.keys():
                slider_widget = self.tableView.indexWidget(self.model.index(row, col))
                sliders[slider_columns[col]] = slider_widget.get_value() if slider_widget else 0

            tool_ability = self.model.item(row, 17).text()

            metric = session.query(ModelMetrics).filter(
                ModelMetrics.connector_name == connector_name,
                ModelMetrics.model_name == model_name
            ).first()
            if metric:
                metric.price = price
                metric.speed = sliders['speed']
                metric.understanding = sliders['understanding']
                metric.summarizing = sliders['summarizing']
                metric.knowledge = sliders['knowledge']
                metric.logical_reasoning = sliders['logical_reasoning']
                metric.math = sliders['math']
                metric.coding = sliders['coding']
                metric.writing = sliders['writing']
                metric.attachment = sliders['attachment']
                metric.image_recognition = sliders['image_recognition']
                metric.image_generation = sliders['image_generation']
                metric.video_generation = sliders['video_generation']
                metric.video_recognition = sliders['video_recognition']
                metric.searching = sliders['searching']
                metric.tool_ability = tool_ability
            else:
                new_record = ModelMetrics(
                    connector_name=connector_name,
                    model_name=model_name,
                    price=price,
                    speed=sliders['speed'],
                    understanding=sliders['understanding'],
                    summarizing=sliders['summarizing'],
                    knowledge=sliders['knowledge'],
                    logical_reasoning=sliders['logical_reasoning'],
                    math=sliders['math'],
                    coding=sliders['coding'],
                    writing=sliders['writing'],
                    attachment=sliders['attachment'],
                    image_recognition=sliders['image_recognition'],
                    image_generation=sliders['image_generation'],
                    video_generation=sliders['video_generation'],
                    video_recognition=sliders['video_recognition'],
                    searching=sliders['searching'],
                    tool_ability=tool_ability,
                )
                session.add(new_record)

        session.commit()
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大语言模型指标管理")
        self.resize(400, 300)

        self.button = QPushButton("模型评测", self)
        self.button.clicked.connect(self.show_dialog)



        layout = QVBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.button_frequent)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def show_dialog(self):
        dialog = ModelEvaluationDialog()
        dialog.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
