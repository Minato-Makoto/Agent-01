@echo off
chcp 65001 >nul
set "PYTHONPATH=%~dp0src"
set "PYTHONUTF8=1"
python "%~dp0simulate_context.py"
pause
