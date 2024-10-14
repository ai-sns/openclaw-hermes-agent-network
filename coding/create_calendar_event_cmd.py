# filename: create_calendar_event_cmd.py
import os
from datetime import datetime, timedelta

# 计算明天的日期和时间
tomorrow = datetime.now() + timedelta(days=1)
meeting_time = tomorrow.replace(hour=8, minute=0, second=0)

# 格式化任务时间
task_time = meeting_time.strftime('%H:%M')

# 创建任务
task_name = 'MeetingReminder'
os.system(f'schtasks /create /tn "{task_name}" /tr "msg * 会议提醒: 您有一个会议安排在明天早上8点！" /sc once /st {task_time} /sd {tomorrow.strftime("%m/%d/%Y")} /f')

print("会议提醒已添加到Windows任务计划。")