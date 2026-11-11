@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found. Set up .venv using README.md first.
  pause
  exit /b 1
)
echo Applying database migrations...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  echo Migration failed. Check that Python dependencies are installed.
  pause
  exit /b 1
)
echo Starting SmartExam API at http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
