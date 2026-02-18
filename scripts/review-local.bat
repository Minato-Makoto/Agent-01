@echo off
setlocal EnableExtensions
pushd "%~dp0.."

echo === git status ===
git status --short
echo.
echo === diff stat ===
git --no-pager diff --stat
echo.

call scripts\lint.bat
if errorlevel 1 (
    popd
    exit /b 1
)
call scripts\test.bat
if errorlevel 1 (
    popd
    exit /b 1
)
call scripts\build.bat
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
