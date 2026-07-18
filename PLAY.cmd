@echo off
setlocal EnableExtensions
call "%~dp0pns-bot.cmd" play %*
exit /b %ERRORLEVEL%
