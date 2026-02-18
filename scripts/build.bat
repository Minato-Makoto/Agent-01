@echo off
setlocal EnableExtensions
pushd "%~dp0.."
python -m compileall -q src
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
