@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ui_dummy_preview] Python was not found in PATH.
  pause
  exit /b 1
)

python -u ui_dummy_preview %*
if errorlevel 1 (
  echo.
  echo [ui_dummy_preview] Exited with error code %errorlevel%.
  pause
)

endlocal
