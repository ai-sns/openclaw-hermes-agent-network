import random
import datetime

# 定义日志级别
LOG_LEVELS = ['INFO', 'ERROR']
# 定义日志格式
LOG_FORMAT = "{timestamp} | {level} | {source} | {message}"

# 模拟日志信息
def generate_log_message(timestamp):
    """生成随机的日志消息"""
    # 模拟一个应用程序的状态信息
    if random.choice([True, False]):
        return f"app amount--- /static-offline-docs --- /data002/lchat/langchain-chat/server/static --- static-offline-docs"
    else:
        server_process_id = random.randint(4100000, 4200000)
        return f"[32mINFO[0m:     Started server process [{[36m{server_process_id}[0m}]"


def generate_logs(start_date, end_date):
    """生成指定日期范围内的日志"""
    current_date = start_date
    logs = []

    while current_date <= end_date:
        # 随机生成时间
        time = datetime.time(random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
        timestamp = datetime.datetime.combine(current_date, time)

        # 生成日志信息
        for _ in range(random.randint(1, 3)):  # 每个时间戳生成1到3条日志
            level = random.choice(LOG_LEVELS)
            source = 'stdout' if level == 'INFO' else 'stderr'
            message = generate_log_message(timestamp)

            log_entry = LOG_FORMAT.format(
                timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                level=level,
                source=source,
                message=message
            )
            logs.append(log_entry)

        # 移动到下一天
        current_date += datetime.timedelta(days=1)

    return logs


def write_logs_to_file(logs, filename='logs.txt'):
    """将日志写入文件"""
    with open(filename, 'w') as log_file:
        for log in logs:
            log_file.write(log + '\n')


if __name__ == "__main__":
    # 定义日期范围
    start_date = datetime.date(2024, 4, 4)
    end_date = datetime.date(2024, 6, 30)

    # 生成日志
    logs = generate_logs(start_date, end_date)
    
    # 写入日志到文件
    write_logs_to_file(logs)

    print(f"日志已生成并写入到文件 'logs.txt'。")