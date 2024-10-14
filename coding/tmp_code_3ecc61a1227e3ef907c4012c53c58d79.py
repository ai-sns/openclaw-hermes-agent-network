import random
from datetime import datetime, timedelta

# 定义日志生成的时间范围
start_date = datetime(2024, 4, 4)
end_date = datetime(2024, 6, 30)

# 日志模板
log_template = "{date} | INFO | stdout | \x1b[32mINFO\x1b[0m:     127.0.0.1:{port} - \"\x1b[1mPOST /v1/chat/completions HTTP/1.1\x1b[0m\" \x1b[32m{status}\x1b[0m"

# 状态码选项
status_codes = ["200 OK", "400 Bad Request"]

# 生成随机时间间隔
def random_timedelta():
    minutes = random.randint(1, 10)
    seconds = random.randint(0, 59)
    return timedelta(minutes=minutes, seconds=seconds)

# 生成指定日期范围内的日志
def generate_logs(start, end):
    current_time = start
    
    while current_time <= end:
        log_count = random.randint(10, 20)
        for _ in range(log_count):
            port = random.randint(1024, 65535)
            status = random.choice(status_codes)
            log_entry = log_template.format(date=current_time.strftime("%Y-%m-%d %H:%M:%S"), port=port, status=status)
            print(log_entry)
            
            # 增加随机时间间隔
            current_time += random_timedelta()
        
        # 更新到下一天
        current_time = datetime.combine(current_time.date() + timedelta(days=1), datetime.min.time())

# 开始生成日志
generate_logs(start_date, end_date)