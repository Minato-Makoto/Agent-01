@echo off
setlocal EnableExtensions
pushd "%~dp0.."

if not defined SETUP_VERBOSE set SETUP_VERBOSE=0

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    popd
    exit /b 1
)

echo [setup] Installing Python dependencies...
if /I "%SETUP_VERBOSE%"=="1" (
    python -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt --disable-pip-version-check --quiet >nul 2>nul
)
if errorlevel 1 (
    echo ERROR: failed to install Python dependencies.
    if /I not "%SETUP_VERBOSE%"=="1" echo Hint: run with SETUP_VERBOSE=1 for full logs.
    popd
    exit /b 1
)

if not defined INSTALL_BROWSER set INSTALL_BROWSER=1
if /I "%INSTALL_BROWSER%"=="1" (
    echo [setup] Installing Playwright Chromium...
    if /I "%SETUP_VERBOSE%"=="1" (
        python -m playwright install chromium
    ) else (
        python -m playwright install chromium >nul 2>nul
    )
    if errorlevel 1 (
        echo ERROR: failed to install Playwright Chromium runtime.
        if /I not "%SETUP_VERBOSE%"=="1" echo Hint: run with SETUP_VERBOSE=1 for full logs.
        popd
        exit /b 1
    )
)

echo [setup] Done.
popd
exit /b 0
