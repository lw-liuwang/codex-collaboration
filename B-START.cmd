@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0worker\Start-B.ps1"
set "workerExit=%ERRORLEVEL%"
echo.
if not "%workerExit%"=="0" echo Setup or recovery did not finish. Read the error above.
pause
exit /b %workerExit%
