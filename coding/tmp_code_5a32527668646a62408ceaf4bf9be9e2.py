import random
from datetime import datetime, timedelta

# 定义日志生成的时间范围
start_date = datetime(2024, 4, 1)
end_date = datetime(2024, 6, 30)

# 日志模板
log_template = "{date} | INFO | stdout | \x1b[32mINFO\x1b[0m:     127.0.0.1:{port} - \"\x1b[1mPOST /v1/chat/completions HTTP/1.1\x1b[0m\" \x1b[32m{status}\x1b[0m"

# 状态码选项
status_codes = ["200 OK", "400 Bad Request"]

# 生成随机时间间隔（1到10分钟）
def random_timedelta():
    minutes = random.randint(1, 10)
    seconds = random.randint(0, 59)
    return timedelta(minutes=minutes, seconds=seconds)

# 生成指定日期范围内的日志并保存到文件中
def generate_logs(start, end, file_path):
    with open(file_path, 'w') as file:
        current_date = start.date()
        while current_date <= end.date():
            current_time = datetime.combine(current_date, datetime.min.time())
            next_day = current_date + timedelta(days=1)
            
            # 每天生成日志，直到当天的24小时涵盖
            while current_time < datetime.combine(next_day, datetime.min.time()):
                port = random.randint(1024, 65535)
                status = random.choice(status_codes)
                log_entry = log_template.format(date=current_time.strftime("%Y-%m-%d %H:%M:%S"), port=port, status=status)
                file.write(log_entry + '\n')
                
                # 增加随机时间间隔
                current_time += random_timedelta()
            
            # 更新到下一天
            current_date = next_day

# 文件保存路径
file_path = r'C:\Download\logs\cjr.log'

# 开始生成日志并保存到文件
generate_logs(start_date, end_date, file_path)