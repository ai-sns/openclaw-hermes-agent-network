import random
from datetime import datetime, timedelta

# 定义日志生成的时间范围
start_date = datetime(2024, 4, 4)
end_date = datetime(2024, 6, 30)

# 日志模板
log_template = "{date} | INFO | stdout | \x1b[32mINFO\x1b[0m:     127.0.0.1:{port} - \"\x1b[1mPOST /v1/chat/completions HTTP/1.1\x1b[0m\" \x1b[32m{status}\x1b[0m"

# 状态码选项
status_codes = ["200 OK", "400 Bad Request"]

# 生成随机时间
def random_time():
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02}:{minute:02}:{second:02}"

# 生成指定日期范围内的日志
def generate_logs(start, end):
    current_date = start
    while current_date <= end:
        # 每天生成随机数量的日志（假设每天10至20条）
        log_count = random.randint(10, 20)
        for _ in range(log_count):
            date_time = f"{current_date.date()} {random_time()}"
            port = random.randint(1024, 65535)
            status = random.choice(status_codes)
            log_entry = log_template.format(date=date_time, port=port, status=status)
            print(log_entry)
        current_date += timedelta(days=1)

# 开始生成日志
generate_logs(start_date, end_date)