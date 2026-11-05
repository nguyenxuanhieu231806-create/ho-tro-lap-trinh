@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
set "result=%errorlevel%"
if not "%result%"=="0" (
  echo Startup failed. Read the message above.
  pause
)
exit /b %result%
