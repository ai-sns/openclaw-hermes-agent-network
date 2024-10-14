# plugins/code_editor.py
import sys

from PyQt5.QtCore import QUrl
from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5 import QtWidgets
from pluginsmanager.plugins_gui.plugins import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineFullScreenRequest, QWebEngineView, QWebEngineProfile, QWebEngineSettings
import sys
import json

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QShortcut
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSlot

import os
from typing import List

import chess
import chess.svg

from IPython.display import display
from typing_extensions import Annotated
made_move = False
class Chess(QWidget,PluginInterface):
    def __init__(self, content=""):
        super().__init__()
        # Initialize the board.
        self.board = chess.Board()
        self.parent=None


        # Keep track of whether a move has been made.

        # 初始化用户界面

    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局

        chess_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(chess_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        chess_webview = QWebEngineView(chess_widget)
        chess_webview.setObjectName("chess")
        chess_webview.setUrl(QUrl("file:///scripts/chess/index.html"))
        self.chess_webview=chess_webview
        layout.addWidget(chess_webview)

        # Create QTextEdit
        self.text_edit = QTextEdit(self)
        self.text_edit.setFixedHeight(80)
        self.text_edit.setPlainText("")
        layout.addWidget(self.text_edit)

        # 创建按钮的水平布局
        button_layout = QHBoxLayout()

        # 创建添加按钮
        hello_button = QPushButton("关闭")
        hello_button.clicked.connect(self.close_tab)  # 连接按钮点击事件到添加函数
        button_layout.addWidget(hello_button)

        # 创建保存按钮
        save_button = QPushButton("AI代下")
        save_button.clicked.connect(self.ai_play)  # 连接保存事件
        button_layout.addWidget(save_button)

        # 创建预览按钮
        preview_button = QPushButton("优化我的AI算法")
        preview_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(preview_button)

        # 创建预览按钮
        import_button = QPushButton("导入算法")
        import_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(import_button)

        # 创建预览按钮
        reset_button = QPushButton("重置算法")
        reset_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(reset_button)

        # 将按钮布局添加到主布局
        layout.addLayout(button_layout)



        # 设置窗口布局
        self.setLayout(layout)
        # 设置窗口标题
        self.setWindowTitle("中国象棋")
        # 设置窗口大小
        self.resize(600, 400)\

    def handle_send_message(self, *args, **kwagrs):
        parent=args[0]
        message = args[1]
        if parent.__class__.__name__=="TaskPage":
            self.parent=parent
            parent.system_role_prompt = """
You are a chess player.
You are playing against another player.
You communicate your move using universal chess interface language.
You should ensure you are making legal moves.
Do not apologize for making illegal moves.
            """
            print("TaskPage")
            print("sending message:",message)
            the_move_desc,the_svg_board,the_txt_board=self.make_move(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")


            return the_move_desc
        elif parent.__class__.__name__=="MessageBox":
            self.parent=parent
            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            Do not apologize for making illegal moves.
                        """
            print("MessageBox")
            print("sending message:",message)
            the_move_desc,the_svg_board,the_txt_board=self.make_move(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")


            return message


    def handle_received_message(self, *args, **kwagrs):
        parent = args[0]
        message = args[1]
        if parent.__class__.__name__=="TaskPage":
            self.parent = parent
            print("TaskPage")
            print("sending message:", message)

            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            You do not need to consider whether it is legal of the move made by another player.
            You can only select move from the possible moves.
                        """

            the_move_desc, the_svg_board, the_txt_board = self.make_move_by_ai(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")

            return the_move_desc

        elif parent.__class__.__name__ == "MessageBox":
            self.parent = parent
            print("MessageBox")
            print("receiveing message:", message)

            parent.system_role_prompt = """
            You are a chess player.
            You are playing against another player.
            You communicate your move using universal chess interface language.
            You should ensure you are making legal moves.
            You do not need to consider whether it is legal of the move made by another player.
            You can only select move from the possible moves.
                        """

            the_move_desc, the_svg_board, the_txt_board = self.make_move_by_ai(message)

            tabs = parent.tabWidget
            chess_view = tabs.findChild(QWebEngineView, "chess")

            chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{the_svg_board}`")

            return the_move_desc


    def close_tab(self):
        """向文本编辑器中添加 'Hello World2'"""
        tab = self.parent().parent()
        if tab:
            # 获取并打印父控件的类型
            print(f"父控件类型是: {type(tab).__name__}")
            current_index = tab.currentIndex()  # 获取当前选中的 Tab 的索引
            if current_index != -1:  # 确保有 Tab 被选中
                # 获取当前 Tab 对应的 Widget
                tab_widget = tab.widget(current_index)
                # 使用 deleteLater() 方法安全地删除该 Widget
                tab_widget.deleteLater()
                tab.removeTab(current_index)  # 移除当前选中的 Tab
        else:
            print("没有父控件。")

    def save_file(self):
        """将编辑器中的文本保存到 coding/mindmap.md"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.md")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息

    def preview_file(self):
        """保存文件并在浏览器中打开"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.html")
        html_txt_head="""
        <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta http-equiv="X-UA-Compatible"content="IE=edge"/><meta name="viewport"content="width=device-width, initial-scale=1.0"/><title>Markmap</title><style>svg.markmap{width:100%;height:100vh}</style><script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script></head><body><div class="markmap"><script type="text/template">
        """
        html_txt_tail="""
        </script></div></body></html>
        """
        html_file_content=html_txt_head+self.editor.toPlainText()+html_txt_tail

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(html_file_content)  # 将文本写入文件


        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件

    @pyqtSlot()
    def ai_play(self):
        command = self.text_edit.toPlainText()
        # self.text_edit.clear()
        # Process the command to extract the chess move
        chess_command = command.strip()
        point = self.extract_point(command)

        # Call JavaScript functions in the web page
        self.chess_webview.page().runJavaScript(f"send_msg('{chess_command}');")
        # self.browser.page().runJavaScript(f"make_move('{chess_command}', {json.dumps(point)});")

    def extract_point(self, command):
        # Here we assume the command is in the format: "马8进7(0827)"
        # Extract the points from the command
        if '(' in command and ')' in command:
            point_str = command[command.index('(') + 1:command.index(')')]
            start = [int(point_str[0]), int(point_str[1])]
            end = [int(point_str[2]), int(point_str[3])]
            return [start, end]
        return []


    def get_legal_moves(self) -> Annotated[str, "A list of legal moves in UCI format"]:
        print("the legal moves:","Possible moves are: " + ",".join([str(move) for move in self.board.legal_moves]))
        self.text_edit.setPlainText("Possible moves are: " + ",".join([str(move) for move in self.board.legal_moves]))
        return "The possible moves are: " + ",".join([str(move) for move in self.board.legal_moves])

    def make_move(self,move: Annotated[str, "A move in UCI format."]) -> Annotated[str, "Result of the move."]:
        print("the move input:",move)
        the_move_desc=""
        the_svg_board=""
        the_txt_board=""

        if not move:
            the_svg_board = chess.svg.board(self.board, size=400)
            print("none move the_svg_board:",the_svg_board)
            return the_move_desc, the_svg_board, the_txt_board


        move = chess.Move.from_uci(move)
        print("the move after:",move)
        self.board.push_uci(str(move))
        global made_move
        made_move = True
        # Display the board.
        thebard=display(
            chess.svg.board(self.board, arrows=[(move.from_square, move.to_square)], fill={move.from_square: "gray"}, size=400)
        )
        print("theboard:",thebard)
        the_svg_board=chess.svg.board(self.board, arrows=[(move.from_square, move.to_square)], fill={move.from_square: "gray"}, size=400)
        print("theboard2:", the_svg_board)
        # Get the piece name.
        piece = self.board.piece_at(move.to_square)
        piece_symbol = piece.unicode_symbol()
        piece_name = (
            chess.piece_name(piece.piece_type).capitalize()
            if piece_symbol.isupper()
            else chess.piece_name(piece.piece_type)
        )

        print("chess.Board:",chess.Board())
        the_txt_board=self.board

        # move=""

        # the_move_desc=f"Moved {piece_name} ({piece_symbol}) from {chess.SQUARE_NAMES[move.from_square]} to {chess.SQUARE_NAMES[move.to_square]}."
        the_move_desc=f"""
        We are playing chess,I play as {"white" if self.parent.chess_role=="black" else "black"},I make a move {move},and now the chess board is :{the_txt_board} You must make sure the move you will provide is chosen from the possible moves.now it is your turn.Please tell me your move that you chose in four characters.
        """


        return the_move_desc,the_svg_board,the_txt_board

    def make_move_by_ai(self,move: Annotated[str, "A move in UCI format."]) -> Annotated[str, "Result of the move."]:
        print("the move input:",move)
        the_move_desc=""
        the_svg_board=""
        the_txt_board=""

        if not move:
            the_svg_board = chess.svg.board(self.board, size=400)
            print("none move the_svg_board:",the_svg_board)
            return the_move_desc, the_svg_board, the_txt_board


        move = chess.Move.from_uci(move)
        print("the move after:",move)
        self.board.push_uci(str(move))
        global made_move
        made_move = True
        # Display the board.
        thebard=display(
            chess.svg.board(self.board, arrows=[(move.from_square, move.to_square)], fill={move.from_square: "gray"}, size=400)
        )
        print("theboard:",thebard)
        the_svg_board=chess.svg.board(self.board, arrows=[(move.from_square, move.to_square)], fill={move.from_square: "gray"}, size=400)
        print("theboard2:", the_svg_board)
        # Get the piece name.
        piece = self.board.piece_at(move.to_square)
        piece_symbol = piece.unicode_symbol()
        piece_name = (
            chess.piece_name(piece.piece_type).capitalize()
            if piece_symbol.isupper()
            else chess.piece_name(piece.piece_type)
        )

        print("chess.Board:",chess.Board())
        print("self.board",self.board)
        the_txt_board=self.board

        the_move=self.get_legal_moves()

        # the_move_desc=f"Moved {piece_name} ({piece_symbol}) from {chess.SQUARE_NAMES[move.from_square]} to {chess.SQUARE_NAMES[move.to_square]}."
        the_move_desc=f"""
        We are playing chess,I play as {"white" if self.parent.chess_role=="black" else "black"},I make a move {move},and now the chess board is :{the_txt_board} now it is your turn.You must choose a move from the following possible moves,{the_move}.You must make sure the move you will provide is chosen from the possible moves.Please tell me your move that you chose in four characters.
        """

        # the_move_desc=f"""
        # We are playing chess,I play as white,I make a move {move},and now the chess board is :{the_txt_board} now it is your turn.Please tell me your move just in four characters
        # """

        return the_move_desc,the_svg_board,the_txt_board
