# filename: add_windows_calendar_event.sh

# Step 1: Create iCalendar file using Python

python3 << EOF
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

create_ics_file()
EOF

# Step 2: Use Windows Task Scheduler to open the .ics file at a specific time (tomorrow at 8 AM)

schtasks /create /tn "MeetingReminder" /tr "start meeting_event.ics" /sc once /st 08:00 /sd $(date -d "tomorrow" +"%Y-%m-%d") /f

echo "The meeting reminder has been scheduled."