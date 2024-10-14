# filename: run_as_admin.bat

@echo off
:: Check for Administrator rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running script with administrator privileges...
    python add_windows_calendar_event.py
) else (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c run_as_admin.bat' -Verb RunAs"
)