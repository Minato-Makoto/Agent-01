@echo off
setlocal EnableExtensions
pushd "%~dp0.."

python -m ruff --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: ruff is not installed. Run: python -m pip install ruff
    popd
    exit /b 1
)

python -m ruff check src
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
