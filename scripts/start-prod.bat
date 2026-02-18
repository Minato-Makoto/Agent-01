@echo off
setlocal EnableExtensions
set NO_PAUSE=1
set AUTO_SETUP=0
call "%~dp0..\run.bat"
exit /b %ERRORLEVEL%
