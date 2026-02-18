@echo off
setlocal EnableExtensions

echo ========================================
echo  AgentForge CLI
echo ========================================
echo.
echo Default mode: LOCAL llama-server (v1.0.1)
echo.

REM ============================================================
REM  CONFIGURATION DEFAULTS
REM  Override by setting env vars before calling run.bat.
REM ============================================================

if not defined PROVIDER set PROVIDER=local
if not defined SERVER_EXE set SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe
if not defined MODEL_PATH set MODEL_PATH=

if not defined BASE_URL set BASE_URL=http://127.0.0.1:8080
if not defined MODEL_ID set MODEL_ID=local
if not defined API_KEY_ENV set API_KEY_ENV=OPENAI_API_KEY

if not defined CTX_SIZE set CTX_SIZE=16384
if not defined GPU_LAYERS set GPU_LAYERS=-1
if not defined THREADS set THREADS=0
if not defined TEMPERATURE set TEMPERATURE=0.1
if not defined TOP_P set TOP_P=0.9
if not defined TOP_K set TOP_K=40
if not defined REPEAT_PENALTY set REPEAT_PENALTY=1.1
if not defined SEED set SEED=-1
if not defined REASONING_FORMAT set REASONING_FORMAT=auto
if not defined REASONING_EFFORT set REASONING_EFFORT=
if not defined MAX_TOKENS set MAX_TOKENS=8192

if not defined HOST set HOST=127.0.0.1
if not defined PORT set PORT=8080

if not defined BOOT_TIMEOUT set BOOT_TIMEOUT=120
if not defined HEALTH_TIMEOUT set HEALTH_TIMEOUT=2
if not defined REQUEST_TIMEOUT set REQUEST_TIMEOUT=300
if not defined COMPAT_RETRY_LIMIT set COMPAT_RETRY_LIMIT=8

if not defined WORKSPACE set WORKSPACE=%~dp0workspace
if not defined EXTRA_ARGS set EXTRA_ARGS=

REM Optional:
REM - AUTO_SETUP=1  : install dependencies automatically (default)
REM - CHECK_ONLY=1  : validate launcher prerequisites and exit without running model/backend
REM - NO_PAUSE=1    : disable pause at script end
if not defined AUTO_SETUP set AUTO_SETUP=1
if not defined CHECK_ONLY set CHECK_ONLY=0
if not defined NO_PAUSE set NO_PAUSE=0

pushd "%~dp0"
set PYTHONPATH=%~dp0src

if not exist "%WORKSPACE%" (
    echo ERROR: Workspace directory not found: %WORKSPACE%
    popd
    if "%NO_PAUSE%"=="0" pause
    exit /b 1
)

if /I "%AUTO_SETUP%"=="1" (
    call "%~dp0scripts\setup.bat"
    if errorlevel 1 (
        echo ERROR: setup failed.
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
)

if /I "%CHECK_ONLY%"=="1" (
    echo CHECK_ONLY=1 passed. Launcher prerequisites look valid.
    popd
    if "%NO_PAUSE%"=="0" pause
    exit /b 0
)

set RUN_ARGS=
if /I "%PROVIDER%"=="local" (
    if "%MODEL_PATH%"=="" (
        echo ERROR: MODEL_PATH is required in local mode.
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
    if not exist "%SERVER_EXE%" (
        echo ERROR: llama-server.exe not found: %SERVER_EXE%
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
    if not exist "%MODEL_PATH%" (
        echo ERROR: model file not found: %MODEL_PATH%
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
    set RUN_ARGS=run "%MODEL_PATH%" --provider local --server-exe "%SERVER_EXE%"
) else if /I "%PROVIDER%"=="openai_compatible" (
    if "%BASE_URL%"=="" (
        echo ERROR: BASE_URL is required in openai_compatible mode.
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
    if "%MODEL_ID%"=="" (
        echo ERROR: MODEL_ID is required in openai_compatible mode.
        popd
        if "%NO_PAUSE%"=="0" pause
        exit /b 1
    )
    set RUN_ARGS=run --provider openai_compatible --base-url "%BASE_URL%" --model-id "%MODEL_ID%" --api-key-env "%API_KEY_ENV%"
) else (
    echo ERROR: invalid PROVIDER value: "%PROVIDER%"
    echo Allowed: local, openai_compatible
    popd
    if "%NO_PAUSE%"=="0" pause
    exit /b 1
)

python -m agentforge.cli %RUN_ARGS% --host "%HOST%" --ctx-size %CTX_SIZE% --gpu-layers %GPU_LAYERS% --threads %THREADS% --temp %TEMPERATURE% --top-p %TOP_P% --top-k %TOP_K% --repeat-penalty %REPEAT_PENALTY% --seed %SEED% --reasoning-format "%REASONING_FORMAT%" --reasoning-effort "%REASONING_EFFORT%" --max-tokens %MAX_TOKENS% --port %PORT% --boot-timeout %BOOT_TIMEOUT% --health-timeout %HEALTH_TIMEOUT% --request-timeout %REQUEST_TIMEOUT% --compat-retry-limit %COMPAT_RETRY_LIMIT% --workspace "%WORKSPACE%" %EXTRA_ARGS%
set EXIT_CODE=%ERRORLEVEL%

popd
if "%NO_PAUSE%"=="0" pause
exit /b %EXIT_CODE%
