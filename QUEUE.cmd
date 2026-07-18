@echo off
setlocal EnableExtensions
call "%~dp0pns-bot.cmd" queue %*
exit /b %ERRORLEVEL%
