@echo off
echo Starting the NOCIA Admin Portal (Port 5000)...
start cmd /k "python app_admin.py"

echo Starting the NOCIA Employee Portal (Port 8000)...
start cmd /k "python app_employee.py"

echo Both portals have been launched in separate windows!
echo - Admin: http://127.0.0.1:5000
echo - Employee: http://127.0.0.1:8000
