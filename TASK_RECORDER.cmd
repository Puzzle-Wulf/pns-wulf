@echo off
setlocal EnableExtensions
call "%~dp0pns-bot.cmd" task-recorder %*
exit /b %ERRORLEVEL%
