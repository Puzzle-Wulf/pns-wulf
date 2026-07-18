@echo off
setlocal EnableExtensions
call "%~dp0pns-bot.cmd" setup %*
exit /b %ERRORLEVEL%
