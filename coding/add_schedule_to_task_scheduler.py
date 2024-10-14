# filename: add_schedule_to_task_scheduler.py
import subprocess
from datetime import datetime, timedelta

# 获取当前日期和时间
current_time = datetime.now()
# 计算明天的日期
tomorrow = current_time + timedelta(days=1)
# 设置提醒时间为明天的9点
reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

# 格式化任务时间以符合SCHTASKS要求
formatted_time = reminder_time.strftime('%H:%M')
formatted_date = reminder_time.strftime('%Y-%m-%d')

# 创建任务的命令
task_name = "FlightReminder"
command = f'SCHTASKS /CREATE /TN "{task_name}" /TR "msg * 这是您的飞机日程提醒。" /SC ONCE /ST {formatted_time} /SD {formatted_date} /F'

# 执行命令
subprocess.run(command, shell=True)

print(f"日程已成功添加到任务计划程序，时间为 {formatted_date} {formatted_time}。")