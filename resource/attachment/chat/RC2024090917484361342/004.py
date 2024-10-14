import os

# 定义文件路径
file_path = r'C:\dev\ai-sns\PyTalk\pytalk\Agent.py'

# 使用 os.path.basename() 获取文件名
file_name = os.path.basename(file_path)

# 输出文件名
print(file_name)  # 输出: Agent.py
