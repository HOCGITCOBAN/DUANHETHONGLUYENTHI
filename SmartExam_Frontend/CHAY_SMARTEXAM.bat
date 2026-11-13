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
powershell -NoProfile -Command "$ready = $false; for ($i = 0; $i -lt 45; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 2; if ($r.StatusCode -eq 200) { $ready = $true; break } } catch {}; Start-Sleep -Seconds 1 }; if (-not $ready) { exit 1 }"
if errorlevel 1 (
  echo Backend did not become ready. Check the SmartExam Backend window for migration or startup errors.
  pause
  exit /b 1
)
echo Backend is ready.
cd /d "%FRONTEND%"
node server.mjs
pause
