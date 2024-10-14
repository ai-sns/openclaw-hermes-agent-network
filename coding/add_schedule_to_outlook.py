# filename: add_schedule_to_outlook.py
import win32com.client
from datetime import datetime, timedelta

# 获取当前日期和时间
current_time = datetime.now()
# 计算明天的日期
tomorrow = current_time + timedelta(days=1)
# 设置提醒时间为明天的9点
reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

# 创建Outlook应用程序对象
outlook = win32com.client.Dispatch("Outlook.Application")
# 创建约会项
appointment = outlook.CreateItem(1)  # 1表示约会项
appointment.Subject = "飞机日程"
appointment.Start = reminder_time
appointment.Duration = 60  # 持续时间为60分钟
appointment.ReminderSet = True
appointment.ReminderMinutesBeforeStart = 15  # 提前15分钟提醒
appointment.Body = "这是您的飞机日程提醒。"
appointment.Location = "机场"  # 可以根据需要设置位置
appointment.Save()  # 保存日程

print("日程已成功添加到Outlook日历。")