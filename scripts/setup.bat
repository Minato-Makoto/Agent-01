@echo off
setlocal EnableExtensions
pushd "%~dp0.."

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    popd
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: failed to install Python dependencies.
    popd
    exit /b 1
)

if not defined INSTALL_BROWSER set INSTALL_BROWSER=1
if /I "%INSTALL_BROWSER%"=="1" (
    python -m playwright install chromium
    if errorlevel 1 (
        echo ERROR: failed to install Playwright Chromium runtime.
        popd
        exit /b 1
    )
)

echo Setup complete.
popd
exit /b 0
