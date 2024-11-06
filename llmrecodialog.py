import sys
import json
import re
from datetime import datetime

import jieba as jieba
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog, \
    QComboBox
from openai import OpenAI
from openai import OpenAI
import time
import SparkApi
from agent.llm import spark
from db.DBFactory import query_PluginMng_All, Session, query_Question_limit
# from questions import QuestionManager
from aichat import AI_spark, AI_kimi
from questions import QuestionManager
from globals import llm_ability,question_speed


class Worker(QThread):
    finished = pyqtSignal()

    def __init__(self, type, num, ui_obj):
        super(Worker, self).__init__()
        # self.qs = qs
        # self.ans = ans
        self.type = type
        self.num = num
        self.ui_obj = ui_obj

    def run(self):
        print(f"参数是：{self.type}")
        self.on_test_model(self.type, self.num, self.ui_obj)
        self.finished.emit()  # 操作完成后发送信号

    def on_test(self, param):
        print("测试操作开始")
        time.sleep(5)
        print("测试操作结束")

    def get_rank(self, text):
        match = re.search(r'综合评分：(\d+)', text)
        if match:
            score = match.group(1)
            print(f"综合评分后面的数字是 {score}")
        else:
            print("未找到综合评分后面的数字")
        return int(score) if score is not None else 0

        # 创建OpenAI客户端，替换"MOONSHOT_API_KEY"为你的API Key

    def on_test_model(self, type, num, ui_obj):
        # print(f"参数是：{param}")
        print("测试操作开始")
        # 获取题目
        session = Session()
        records = query_Question_limit(num=num, tag=type)
        qs = [r.question for r in records]
        # 获取答案
        spark = AI_spark()
        answers = spark.ask(qs)
        ans = answers
        # 获取评分
        kimi = AI_kimi()
        rank = 0
        for i in range(len(qs)):
            q = qs[i]
            a = ans[i]
            prompt = f'''
            请根据以下问题和答案，评估大模型对问题的理解能力。你需要考虑答案的准确性、相关性以及是否完全回答了问题。同时，请注意大模型在解释概念时的清晰度和逻辑性。
            问题: {q}
            答案: {a}
            评估:
            准确性: 答案是否正确地描述了问题？
            相关性: 答案是否与问题相关？
            完整性: 答案是否完全回答了问题？
            清晰度和逻辑性: 答案是否清晰易懂，逻辑是否连贯？
            请根据你的评估，给出对大模型理解能力的评分（1-10），并提供简短的解释来支持你的评分。
            综合评分：
            解释：
            '''
            # print(list(answers))
            answers = kimi.ask([prompt])
            r = answers[0]
            print(r)
            rank += self.get_rank(r)
            print("rank-->:", rank)
        print("测试操作结束")
        rank = int(round(rank / len(qs), 1) * 10)
        ui_obj.setText(str(rank))


class EvalApp(QDialog):
    def __init__(self, parent=None, res=None):
        # super(EvalApp, self).__init__(parent,res)
        super().__init__(parent)
        self.qs = []
        self.ans = []
        self.rank = 0
        self.res = res
        self.initUI()

    def initUI(self):
        # 创建垂直布局
        main_layout = QVBoxLayout()

        # 连接器名称输入字段
        connector_layout = QHBoxLayout()
        connector_layout.addWidget(QLabel('连接器名称:'))
        self.connector_name_edit = QComboBox()
        # self.connector_name_edit.setText('讯飞星火')
        connector_layout.addWidget(self.connector_name_edit)
        agents = query_PluginMng_All(is_delete=0, plugin_type="LLM_Connector")
        agent_dict = [f"{agent.name}" for agent in agents]
        self.connector_name_edit.addItems(agent_dict)
        main_layout.addLayout(connector_layout)

        # 模型名称输入字段
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel('模型名称:'))
        self.model_name_edit = QLineEdit()
        # 设置默认值
        self.model_name_edit.setText('讯飞星火')
        model_layout.addWidget(self.model_name_edit)
        main_layout.addLayout(model_layout)

        # 价格输入字段
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel('价格:'))
        self.price_edit = QLineEdit()
        price_layout.addWidget(self.price_edit)
        main_layout.addLayout(price_layout)

        # 速度输入字段
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel('速度:'))
        self.speed_edit = QLineEdit()
        speed_layout.addWidget(self.speed_edit)
        # settings_button0 = QPushButton('设置')
        test_button0 = QPushButton('测试')
        # speed_layout.addWidget(settings_button0)
        speed_layout.addWidget(test_button0)
        main_layout.addLayout(speed_layout)

        # 1 理解能力输入字段和设置、测试按钮
        understanding_layout = QHBoxLayout()
        understanding_layout.addWidget(QLabel('理解能力:'))
        self.understanding_edit = QLineEdit()
        understanding_layout.addWidget(self.understanding_edit)
        settings_button1 = QPushButton('设置')
        test_button1 = QPushButton('测试')
        understanding_layout.addWidget(settings_button1)
        understanding_layout.addWidget(test_button1)
        main_layout.addLayout(understanding_layout)

        # 2 总结能力输入字段和设置、测试按钮
        summarization_layout = QHBoxLayout()
        summarization_layout.addWidget(QLabel('总结能力:'))
        self.summarization_edit = QLineEdit()
        summarization_layout.addWidget(self.summarization_edit)
        settings_button_2 = QPushButton('设置')
        test_button_2 = QPushButton('测试')
        summarization_layout.addWidget(settings_button_2)
        summarization_layout.addWidget(test_button_2)
        main_layout.addLayout(summarization_layout)

        # 3 知识面能力输入字段和设置、测试按钮
        Knowledge_layout = QHBoxLayout()
        Knowledge_layout.addWidget(QLabel('知识面:'))
        self.Knowledge_edit = QLineEdit()
        Knowledge_layout.addWidget(self.Knowledge_edit)
        settings_button_3 = QPushButton('设置')
        test_button_3 = QPushButton('测试')
        Knowledge_layout.addWidget(settings_button_3)
        Knowledge_layout.addWidget(test_button_3)
        main_layout.addLayout(Knowledge_layout)

        # 4 逻辑推理 能力输入字段和设置、测试按钮
        Logical_layout = QHBoxLayout()
        Logical_layout.addWidget(QLabel('逻辑推理:'))
        self.Logical_edit = QLineEdit()
        Logical_layout.addWidget(self.Logical_edit)
        settings_button_4 = QPushButton('设置')
        test_button_4 = QPushButton('测试')
        Logical_layout.addWidget(settings_button_4)
        Logical_layout.addWidget(test_button_4)
        main_layout.addLayout(Logical_layout)

        # 5 数学计算 能力输入字段和设置、测试按钮
        math_layout = QHBoxLayout()
        math_layout.addWidget(QLabel('数学计算:'))
        self.math_edit = QLineEdit()
        math_layout.addWidget(self.math_edit)
        settings_button_5 = QPushButton('设置')
        test_button_5 = QPushButton('测试')
        math_layout.addWidget(settings_button_5)
        math_layout.addWidget(test_button_5)
        main_layout.addLayout(math_layout)

        # 6 代码编程 能力输入字段和设置、测试按钮
        coding_layout = QHBoxLayout()
        coding_layout.addWidget(QLabel('代码编程:'))
        self.coding_edit = QLineEdit()
        coding_layout.addWidget(self.coding_edit)
        settings_button_6 = QPushButton('设置')
        test_button_6 = QPushButton('测试')
        coding_layout.addWidget(settings_button_6)
        coding_layout.addWidget(test_button_6)
        main_layout.addLayout(coding_layout)

        # 7 创作写作文档 能力输入字段和设置、测试按钮
        creation_layout = QHBoxLayout()
        creation_layout.addWidget(QLabel('创作写作文档:'))
        self.creation_edit = QLineEdit()
        creation_layout.addWidget(self.creation_edit)
        settings_button_7 = QPushButton('设置')
        test_button_7 = QPushButton('测试')
        creation_layout.addWidget(settings_button_7)
        creation_layout.addWidget(test_button_7)
        main_layout.addLayout(creation_layout)

        # 8 附件能力 能力输入字段和设置、测试按钮
        attach_layout = QHBoxLayout()
        attach_layout.addWidget(QLabel('附件能力:'))
        self.attach_edit = QLineEdit()
        attach_layout.addWidget(self.attach_edit)
        settings_button_8 = QPushButton('设置')
        test_button_8 = QPushButton('测试')
        attach_layout.addWidget(settings_button_8)
        attach_layout.addWidget(test_button_8)
        main_layout.addLayout(attach_layout)

        # 9 图文识别能力 能力输入字段和设置、测试按钮  image_rec
        image_rec_layout = QHBoxLayout()
        image_rec_layout.addWidget(QLabel('图文识别能力:'))
        self.image_rec_edit = QLineEdit()
        image_rec_layout.addWidget(self.image_rec_edit)
        settings_button_9 = QPushButton('设置')
        test_button_9 = QPushButton('测试')
        image_rec_layout.addWidget(settings_button_9)
        image_rec_layout.addWidget(test_button_9)
        main_layout.addLayout(image_rec_layout)

        # 10 图片生成能力 能力输入字段和设置、测试按钮
        image_gen_layout = QHBoxLayout()
        image_gen_layout.addWidget(QLabel('图片生成能力:'))
        self.image_gen_edit = QLineEdit()
        image_gen_layout.addWidget(self.image_gen_edit)
        settings_button_10 = QPushButton('设置')
        test_button_10 = QPushButton('测试')
        image_gen_layout.addWidget(settings_button_10)
        image_gen_layout.addWidget(test_button_10)
        main_layout.addLayout(image_gen_layout)

        # 11 视频生成能力 能力输入字段和设置、测试按钮
        video_gen_layout = QHBoxLayout()
        video_gen_layout.addWidget(QLabel('视频生成能力:'))
        self.video_gen_edit = QLineEdit()
        video_gen_layout.addWidget(self.video_gen_edit)
        settings_button_11 = QPushButton('设置')
        test_button_11 = QPushButton('测试')
        video_gen_layout.addWidget(settings_button_11)
        video_gen_layout.addWidget(test_button_11)
        main_layout.addLayout(video_gen_layout)

        # 12 视频识别能力 能力输入字段和设置、测试按钮
        video_rec_layout = QHBoxLayout()
        video_rec_layout.addWidget(QLabel('视频识别能力:'))
        self.video_rec_edit = QLineEdit()
        video_rec_layout.addWidget(self.video_rec_edit)
        settings_button_12 = QPushButton('设置')
        test_button_12 = QPushButton('测试')
        video_rec_layout.addWidget(settings_button_12)
        video_rec_layout.addWidget(test_button_12)
        main_layout.addLayout(video_rec_layout)

        # 13 搜索能力 能力输入字段和设置、测试按钮
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('搜索能力:'))
        self.search_edit = QLineEdit()
        search_layout.addWidget(self.search_edit)
        settings_button_13 = QPushButton('设置')
        test_button_13 = QPushButton('测试')
        search_layout.addWidget(settings_button_13)
        search_layout.addWidget(test_button_13)
        main_layout.addLayout(search_layout)

        # 工具能力 输入字段
        tools_layout = QHBoxLayout()
        tools_layout.addWidget(QLabel('工具能力:'))
        self.tools_edit = QLineEdit()
        tools_layout.addWidget(self.tools_edit)
        main_layout.addLayout(tools_layout)

        if self.res is not None:
            row = self.res
            index = self.connector_name_edit.findText(row.connector_name)
            if index >= 0:
                self.connector_name_edit.setCurrentIndex(index)
            # self.connector_name_edit.setCurrentText(row.connector_name)
            self.model_name_edit.setText(row.model_name)
            self.price_edit.setText(str(row.price))
            self.speed_edit.setText(str(row.speed))
            self.understanding_edit.setText(str(row.understanding))
            self.summarization_edit.setText(str(row.summarizing))

            self.Knowledge_edit.setText(str(row.knowledge))
            self.Logical_edit.setText(str(row.logical_reasoning))
            self.math_edit.setText(str(row.math))
            self.coding_edit.setText(str(row.coding))

            self.creation_edit.setText(str(row.writing))
            self.attach_edit.setText(str(row.attachment))
            self.image_rec_edit.setText(str(row.image_recognition))
            self.image_gen_edit.setText(str(row.image_generation))

            self.video_gen_edit.setText(str(row.video_generation))
            self.video_rec_edit.setText(str(row.video_recognition))
            self.search_edit.setText(str(row.searching))

            self.tools_edit.setText(str(row.tool_ability))

        # OK 和 Cancel 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton('OK')
        cancel_button = QPushButton('Cancel')
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        # 设置窗口的布局和标题
        self.setLayout(main_layout)
        self.setWindowTitle('模型评估')

        # 连接按钮事件
        test_button0.clicked.connect(self.on_test0)
        settings_button1.clicked.connect(self.on_settings1)
        test_button1.clicked.connect(self.on_test1)
        settings_button_2.clicked.connect(self.on_settings2)
        test_button_2.clicked.connect(self.on_test2)
        settings_button_3.clicked.connect(self.on_settings3)
        test_button_3.clicked.connect(self.on_test3)
        settings_button_4.clicked.connect(self.on_settings4)
        test_button_4.clicked.connect(self.on_test4)
        settings_button_5.clicked.connect(self.on_settings5)
        test_button_5.clicked.connect(self.on_test5)
        settings_button_6.clicked.connect(self.on_settings6)
        test_button_6.clicked.connect(self.on_test6)
        settings_button_7.clicked.connect(self.on_settings7)
        test_button_7.clicked.connect(self.on_test7)
        settings_button_8.clicked.connect(self.on_settings8)
        test_button_8.clicked.connect(self.on_test8)
        settings_button_9.clicked.connect(self.on_settings9)
        test_button_9.clicked.connect(self.on_test9)
        settings_button_10.clicked.connect(self.on_settings10)
        test_button_10.clicked.connect(self.on_test10)
        settings_button_11.clicked.connect(self.on_settings11)
        test_button_11.clicked.connect(self.on_test11)
        settings_button_12.clicked.connect(self.on_settings12)
        test_button_12.clicked.connect(self.on_test12)
        settings_button_13.clicked.connect(self.on_settings13)
        test_button_13.clicked.connect(self.on_test13)

        ok_button.clicked.connect(self.on_ok)
        cancel_button.clicked.connect(self.on_cancel)





    def on_settings(self):
        # 打开设置窗口或执行设置相关操作
        print("设置按钮被点击")
        spark = AI_spark()
        questions = self.read_json("question1.json", "question_1", 2)
        self.qs = questions
        answers = spark.ask(questions)
        self.ans = answers
        print(answers)

    def on_settings1(self):
        # 打开设置窗口或执行设置相关操作
        print("设置按钮被点击")
        self.question_manager = QuestionManager(self)
        self.question_manager.exec_()

    def on_settings2(self):
       self.on_settings1()

    def on_settings3(self):
       self.on_settings1()

    def on_settings4(self):
       self.on_settings1()

    def on_settings5(self):
        self.on_settings1()

    def on_settings6(self):
        self.on_settings1()

    def on_settings7(self):
        self.on_settings1()

    def on_settings8(self):
        self.on_settings1()

    def on_settings9(self):
        self.on_settings1()

    def on_settings10(self):
        self.on_settings1()

    def on_settings11(self):
        self.on_settings1()

    def on_settings12(self):
        self.on_settings1()

    def on_settings13(self):
        self.on_settings1()

    def on_test(self,question_type:str=llm_ability[0]):
        # 执行测试操作
        print("测试按钮被点击")
        bt = self.sender()
        # bt.setEnabled(False)
        bt.setCursor(QCursor(Qt.WaitCursor))
        # question_type = llm_ability[0]
        question_num = 3
        self.thread = Worker(question_type, question_num, self.understanding_edit)
        self.thread.finished.connect(self.on_thread_finished1)
        self.thread.start()

    def on_test0(self):
        print("测试按钮被点击")
        spark = AI_spark()
        prompt = question_speed
        time_start= datetime.now()
        answers = spark.ask_one(prompt)
        answers = ''.join(answers)
        time_end  = datetime.now()
        tokens = jieba.cut(answers, cut_all=False)  # 精确模式
        dur = (time_end-time_start)
        lst = list(tokens)
        speed = round(len(lst)/dur.total_seconds(),0)
        self.speed_edit.setText(str(speed))

    def on_test1(self):
        self.on_test(llm_ability[0])

    def on_test2(self):
        self.on_test(llm_ability[1])

    def on_test3(self):
        self.on_test(llm_ability[2])

    def on_test4(self):
        self.on_test(llm_ability[3])

    def on_test5(self):
        self.on_test(llm_ability[4])

    def on_test6(self):
        self.on_test(llm_ability[5])

    def on_test7(self):
        self.on_test(llm_ability[6])

    def on_test8(self):
        self.on_test(llm_ability[7])

    def on_test9(self):
        self.on_test(llm_ability[8])

    def on_test10(self):
        self.on_test(llm_ability[9])

    def on_test11(self):
        self.on_test(llm_ability[10])

    def on_test12(self):
        self.on_test(llm_ability[11])

    def on_test13(self):
        self.on_test(llm_ability[12])


    def on_thread_finished1(self):
        print("线程完成")
        # self.button.setEnabled(True)
        # self.button.setCursor(QCursor(Qt.ArrowCursor))
        # print("线程完成")

    def on_ok(self):
        # 处理用户点击OK按钮的逻辑
        print("OK按钮被点击")
        # self.close()
        self.result = f"{self.connector_name_edit.currentText()},{self.model_name_edit.text()}, {self.price_edit.text()}, " \
                      f"{self.speed_edit.text()} , {self.understanding_edit.text()}, {self.summarization_edit.text()}," \
                      f" {self.Knowledge_edit.text()}, {self.Logical_edit.text()}, {self.math_edit.text()}, {self.coding_edit.text()}," \
                      f" {self.creation_edit.text()}, {self.attach_edit.text()}, {self.image_rec_edit.text()}, {self.image_gen_edit.text()}," \
                      f" {self.video_gen_edit.text()}, {self.video_rec_edit.text()}, {self.search_edit.text()}, {self.tools_edit.text()}        "
        self.accept()  # 关闭对话框并返回

    def on_cancel(self):
        # 处理用户点击Cancel按钮的逻辑
        print("Cancel按钮被点击")
        self.reject()

    def get_result(self):
        return self.result  # 提供一个方法来获取结果

    def read_json(self, file_name, node_name, limit: int = 0):
        # 打开JSON文件
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                # 使用json.load()函数加载并解析JSON数据
                data = json.load(file)
            questions = data[node_name]
            if limit > 0:
                questions = questions[:limit]
        except Exception as e:
            return []

        return questions

    def get_rank(self, text):
        match = re.search(r'综合评分：(\d+)', text)
        if match:
            score = match.group(1)
            print(f"综合评分后面的数字是 {score}")
        else:
            print("未找到综合评分后面的数字")
        return int(score) if score is not None else 0

        # 创建OpenAI客户端，替换"MOONSHOT_API_KEY"为你的API Key


# class AI_kimi:
#     def __init__(self, temperature=0.3):
#         self.api_key = "sk-LpAw4Go0TCRY7ZGRGWwpxU2c1C5uAVy0N3jN9M4XLg0ZkhOq"
#         self.client = self.create_client(self.api_key)
#         self.messages = {"role": "system", "content": "你是Kimi，由Moonshot AI提供的人工智能助手..."}
#         self.model = "moonshot-v1-128k"
#         self.temperature = temperature
#
#     def create_client(self, api_key):
#         client = OpenAI(
#             api_key=api_key,
#             base_url="https://api.moonshot.cn/v1"
#         )
#         return client
#
#     def get_client(self):
#         return self.client
#
#     # 发送对话请求
#     def ask(self, questions):
#         messages = []
#         answers = []
#         for q in questions:
#             messages = []
#             messages.append(self.messages)
#             messages.append({"role": "user", "content": q})
#             try:
#                 completion = self.client.chat.completions.create(
#                     model=self.model,  # 使用Kimi的模型
#                     messages=messages,
#                     temperature=self.temperature,  # 控制生成内容的随机性
#                 )
#                 # 打印Kimi的回答
#
#                 answer = (completion.choices[0].message.content)
#
#                 answers.append(completion.choices[0].message.content)
#                 print({"q": q, "a": answer})
#             except Exception as e:
#                 print(str(e))
#             time.sleep(0.5)
#         # print(answer)
#         return (answers)
#
#
# class AI_spark:
#     def __init__(self):
#         self.appid = 'f2b807e2'
#         self.api_key = "df1c1e0a354053264f400b2ebf85d5cf"
#         self.api_secret = "YzIyM2Y0MTMyZjViMGNhZjdkMDkxZGI5"
#         self.domain = "generalv3.5"  # v3版本
#         self.Spark_url = "wss://spark-api.xf-yun.com/v3.5/chat"  # v3环境的地址（"wss://spark-api.xf-yun.com/v3.1/chat）
#         self.text = []
#
#     def getText(self, role, content):
#         jsoncon = {}
#         jsoncon["role"] = role
#         jsoncon["content"] = content
#         self.text.append(jsoncon)
#         return self.text
#
#     def getlength(self, text):
#         length = 0
#         for content in text:
#             temp = content["content"]
#             leng = len(temp)
#             length += leng
#         return length
#
#     def checklen(self, text):
#         while (self.getlength(text) > 8000):
#             del text[0]
#         return text
#
#     def ask(self, questions):
#         answers = []
#         for q in questions:
#             question = self.checklen(self.getText("user", q))
#             SparkApi.answer = ""
#             SparkApi.main(self.appid, self.api_key, self.api_secret, self.Spark_url, self.domain, question)
#             print("-->", SparkApi.answer)
#             ass = self.getText("assistant", SparkApi.answer)
#             answers.append(SparkApi.answer)
#         return answers
#
#     def ask_one(self,q):
#         answers = []
#         question = self.checklen(self.getText("user", q))
#         SparkApi.answer = ""
#         SparkApi.main(self.appid, self.api_key, self.api_secret, self.Spark_url, self.domain, question)
#         print("-->", SparkApi.answer)
#         # ass = self.getText("assistant", SparkApi.answer)
#         ass = SparkApi.answer
#         questions = ass.strip().split('\n')
#         # 遍历每个问题，进一步拆分内容
#         for question in questions:
#             # 移除每个问题前的编号和“问题：”字样
#             # content = question.replace('问题：', '').strip()
#             content = re.sub(r'^\d+\.\s*问题：\s*', '', question)
#             # 将拆分后的内容添加到列表中
#             answers.append(content)
#
#
#         return answers

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EvalApp()
    ex.show()
    sys.exit(app.exec_())
