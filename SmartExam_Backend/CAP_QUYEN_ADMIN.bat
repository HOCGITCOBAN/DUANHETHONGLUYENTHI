@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found. Set up .venv using README.md first.
  pause
  exit /b 1
)
echo Grant admin access to an existing registered account in your local database.
".venv\Scripts\python.exe" -m app.manage_admin
if errorlevel 1 (
  echo Admin access was not changed. Read the message above.
  pause
  exit /b 1
)
pause
