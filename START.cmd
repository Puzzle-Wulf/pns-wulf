@echo off
setlocal EnableExtensions
call "%~dp0pns-bot.cmd" start %*
exit /b %ERRORLEVEL%
