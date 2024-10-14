import random
import datetime

# 日志级别列表
log_levels = ['INFO', 'ERROR']

# 日志输出类型列表
log_outputs = ['stdout', 'stderr']

# 生成随机的日期时间
def random_datetime(start, end):
    # 生成随机秒数
    random_seconds = random.randint(0, int((end - start).total_seconds()))
    # 计算随机日期时间
    return start + datetime.timedelta(seconds=random_seconds)

# 生成随机的日志内容
def generate_log_content():
    return f"app amount--- /static-offline-docs --- /data002/lchat/langchain-chat/server/static --- static-offline-docs"

# 生成随机的标准输出日志
def generate_info_log():
    return f"[32mINFO[0m:     Started server process [[36m{random.randint(1000000, 9999999)}[0m]"

# 生成随机的标准错误日志
def generate_error_log():
    return random.choice([
        "[32mINFO[0m:     Waiting for application startup.",
        "[32mINFO[0m:     Application startup complete.",
        "[32mINFO[0m:     Uvicorn running on [1mhttp://0.0.0.0:20000[0m (Press CTRL+C to quit)",
        "[31mERROR[0m:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 20000): address already in use",
        "[32mINFO[0m:     Waiting for application shutdown.",
        "[32mINFO[0m:     Application shutdown complete."
    ])

# 生成随机的 HTTP 请求日志
def generate_http_log():
    response_code = random.choice([200, 400])
    return f"[32mINFO[0m:     127.0.0.1:{random.randint(30000, 60000)} - \"[1mPOST /v1/chat/completions HTTP/1.1[0m\" [32m{response_code} OK[0m"

# 生成日志行
def generate_log_line(timestamp):
    log_level = random.choice(log_levels)
    log_output = random.choice(log_outputs)
    
    if log_level == 'INFO' and log_output == 'stdout':
        return f"{timestamp} | INFO | stdout | {generate_log_content()}"
    elif log_level == 'ERROR' and log_output == 'stderr':
        return f"{timestamp} | ERROR | stderr | {generate_error_log()}"
    elif log_level == 'INFO' and log_output == 'stderr':
        return f"{timestamp} | INFO | stdout | {generate_http_log()}"
    else:
        return f"{timestamp} | ERROR | stderr | {generate_error_log()}"

# 主函数
def main():
    # 定义开始和结束日期
    start_date = datetime.datetime(2024, 4, 4, 0, 0, 0)
    end_date = datetime.datetime(2024, 6, 30, 23, 59, 59)

    # 生成日志
    current_date = start_date
    while current_date <= end_date:
        timestamp = current_date.strftime('%Y-%m-%d %H:%M:%S')
        log_line = generate_log_line(timestamp)
        print(log_line)
        # 增加随机时间间隔
        current_date += datetime.timedelta(minutes=random.randint(1, 60))

if __name__ == "__main__":
    main()