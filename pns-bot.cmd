@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
py -3 -m pns_wulf %*
set "RC=%ERRORLEVEL%"
if "%RC%"=="9009" (
  python -m pns_wulf %*
  set "RC=%ERRORLEVEL%"
)
exit /b %RC%
