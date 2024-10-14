# filename: add_calendar_event.py

import win32com.client
from datetime import datetime, timedelta

def add_calendar_event():
    # Creating the Outlook application
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    # Accessing the Calendar folder
    calendar_folder = namespace.GetDefaultFolder(9)  # 9 corresponds to the Calendar folder

    # Creating a new appointment
    appointment = calendar_folder.Items.Add("IPM.Appointment")

    # Setting the appointment details
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    appointment.Start = start_time.strftime("%Y-%m-%d %H:%M:%S")
    appointment.Duration = 60  # Duration in minutes
    appointment.Subject = "Meeting"
    appointment.Body = "This is a meeting scheduled for tomorrow at 8 AM."
    appointment.Location = "Your Location"

    # Saving the appointment
    appointment.Save()
    print("The appointment has been added to your calendar.")

add_calendar_event()