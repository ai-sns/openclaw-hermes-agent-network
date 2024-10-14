# filename: create_schedule_reminder.py
from datetime import datetime, timedelta

# 获取当前日期和时间
current_time = datetime.now()
# 计算明天的日期
tomorrow = current_time + timedelta(days=1)
# 设置提醒时间为明天的9点
reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

# 输出提醒信息
reminder_message = f"提醒: 您的飞机日程定于明天 {reminder_time.strftime('%Y-%m-%d %H:%M')}。"
print(reminder_message)