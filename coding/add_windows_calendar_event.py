# filename: add_windows_calendar_event.py

import subprocess
from datetime import datetime, timedelta

def create_ics_file():
    # Calculate tomorrow's date
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    start_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)

    # Format time for .ics file
    start_time_str = start_time.strftime("%Y%m%dT%H%M%S")
    end_time_str = end_time.strftime("%Y%m%dT%H%M%S")

    # Create the .ics file content
    ics_content = f"""
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Product//Your Product Version//EN
BEGIN:VEVENT
UID:{now.strftime("%Y%m%dT%H%M%S")}-meeting@example.com
DTSTAMP:{now.strftime("%Y%m%dT%H%M%S")}
DTSTART:{start_time_str}
DTEND:{end_time_str}
SUMMARY:Meeting
DESCRIPTION:This is a meeting scheduled for tomorrow at 8 AM.
END:VEVENT
END:VCALENDAR
    """.strip()

    # Write the .ics file
    with open("meeting_event.ics", "w") as file:
        file.write(ics_content)
    print("meeting_event.ics file has been created.")

def schedule_task():
    # Calculate tomorrow's date
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")
    time_str = "08:00"

    # Command to create scheduled task
    command = [
        "schtasks",
        "/create",
        "/tn", "MeetingReminder",
        "/tr", f"start {__file__.replace('.py', '.ics')}",
        "/sc", "once",
        "/st", time_str,
        "/sd", date_str,
        "/f"
    ]
    
    # Run the command
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)

def main():
    create_ics_file()
    schedule_task()

main()