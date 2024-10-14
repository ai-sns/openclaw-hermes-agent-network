# filename: create_calendar_event.py
import win32com.client
from datetime import datetime, timedelta

# 计算明天的日期和时间
tomorrow = datetime.now() + timedelta(days=1)
meeting_time = tomorrow.replace(hour=8, minute=0, second=0)

# 创建任务计划
scheduler = win32com.client.Dispatch('Schedule.Service')
scheduler.Connect()

# 创建新的任务定义
task_def = scheduler.NewTask(0)
task_def.RegistrationInfo.Description = '会议提醒'
task_def.Principal.UserId = 'SYSTEM'
task_def.Principal.LogonType = 3  # Logon interactively

# 设置触发器
trigger = task_def.Triggers.Create(1)  # 1表示时间触发器
trigger.StartBoundary = meeting_time.isoformat() + 'Z'

# 创建操作
exec_action = task_def.Actions.Create(0)  # 0表示执行操作
exec_action.Path = 'powershell.exe'
exec_action.Arguments = '-Command "New-BurntToastNotification -Text \'会议提醒\', \'您有一个会议安排在明天早上8点！\'"'

# 注册任务
task_name = 'MeetingReminder'
scheduler.GetFolder('\\').RegisterTaskDefinition(
    task_name,
    task_def,
    6,  # Replace if exists
    None,
    None,
    3,  # Logon interactively
    None
)

print("会议提醒已添加到Windows日历。")