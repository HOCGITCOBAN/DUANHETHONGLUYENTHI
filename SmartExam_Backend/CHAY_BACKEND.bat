@echo off
cd /d "%~dp0"
echo Applying database migrations...
python -m alembic upgrade head
if errorlevel 1 (
  echo Migration failed. Check that Python dependencies are installed.
  pause
  exit /b 1
)
echo Starting SmartExam API at http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
