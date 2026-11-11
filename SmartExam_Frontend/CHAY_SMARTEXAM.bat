@echo off
setlocal
set "FRONTEND=%~dp0"
for %%I in ("%FRONTEND%..\SmartExam_Backend") do set "BACKEND=%%~fI"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and backend dependencies first.
  pause
  exit /b 1
)

start "SmartExam Backend" "%BACKEND%\CHAY_BACKEND.bat"
echo Starting the backend and applying database migrations...
timeout /t 4 /nobreak >nul
cd /d "%FRONTEND%"
node server.mjs
pause
