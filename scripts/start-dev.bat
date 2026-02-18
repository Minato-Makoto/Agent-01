@echo off
setlocal EnableExtensions
set NO_PAUSE=0
call "%~dp0..\run.bat"
exit /b %ERRORLEVEL%
