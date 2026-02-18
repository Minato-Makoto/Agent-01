@echo off
setlocal EnableExtensions
pushd "%~dp0.."
set PYTHONPATH=%CD%\src
python -m pytest -q
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
