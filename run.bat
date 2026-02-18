@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 (
    echo ERROR: cannot access repository directory.
    exit /b 1
)
set "PYTHONPATH=%~dp0src"

REM ============================================================
REM Agent-01 launcher (Windows-only, single file)
REM
REM How to use:
REM   1) Edit defaults below, or
REM   2) Override per run: set VAR=value && run.bat
REM
REM Quick examples:
REM   Local:
REM     set PROVIDER=local
REM     set SERVER_EXE=D:\tools\llama-server.exe
REM     set MODEL_PATH=D:\models\my-model.gguf
REM     run.bat
REM
REM   Remote:
REM     set PROVIDER=openai_compatible
REM     set BASE_URL=https://api.openai.com/v1
REM     set MODEL_ID=gpt-5-mini
REM     set OPENAI_API_KEY=YOUR_KEY
REM     run.bat
REM
REM Parameter map:
REM   PROVIDER -> --provider
REM   SERVER_EXE -> --server-exe
REM   MODEL_PATH -> positional model
REM   BASE_URL -> --base-url
REM   MODEL_ID -> --model-id
REM   API_KEY_ENV -> --api-key-env
REM   CTX_SIZE -> --ctx-size
REM   GPU_LAYERS -> --gpu-layers
REM   THREADS -> --threads
REM   TEMPERATURE -> --temp
REM   TOP_P -> --top-p
REM   TOP_K -> --top-k
REM   REPEAT_PENALTY -> --repeat-penalty
REM   SEED -> --seed
REM   REASONING_FORMAT -> --reasoning-format
REM   REASONING_EFFORT -> --reasoning-effort
REM   MAX_TOKENS -> --max-tokens
REM   HOST -> --host
REM   PORT -> --port
REM   BOOT_TIMEOUT -> --boot-timeout
REM   HEALTH_TIMEOUT -> --health-timeout
REM   REQUEST_TIMEOUT -> --request-timeout
REM   COMPAT_RETRY_LIMIT -> --compat-retry-limit
REM   MAX_REQUESTS_PER_MINUTE -> --max-requests-per-minute
REM   SHUTDOWN_TIMEOUT -> --shutdown-timeout
REM   MAX_ITERATIONS -> --max-iterations
REM   MAX_REPEATS -> --max-repeats
REM   AGENT_TIMEOUT -> --agent-timeout
REM   WORKSPACE -> --workspace
REM   EXTRA_ARGS -> raw passthrough arguments
REM ============================================================

REM ---- Provider mode ----
if not defined PROVIDER set "PROVIDER=local"

REM ---- Local backend (required when PROVIDER=local) ----
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH="

REM ---- Remote backend (required when PROVIDER=openai_compatible) ----
if not defined BASE_URL set "BASE_URL=http://127.0.0.1:8080"
if not defined MODEL_ID set "MODEL_ID=local"
if not defined API_KEY_ENV set "API_KEY_ENV=OPENAI_API_KEY"

REM ---- Inference tuning ----
if not defined CTX_SIZE set "CTX_SIZE=16384"
if not defined GPU_LAYERS set "GPU_LAYERS=-1"
if not defined THREADS set "THREADS=0"
if not defined TEMPERATURE set "TEMPERATURE=0.1"
if not defined TOP_P set "TOP_P=0.9"
if not defined TOP_K set "TOP_K=40"
if not defined REPEAT_PENALTY set "REPEAT_PENALTY=1.1"
if not defined SEED set "SEED=-1"
if not defined REASONING_FORMAT set "REASONING_FORMAT=auto"
if not defined REASONING_EFFORT set "REASONING_EFFORT=low"
if not defined MAX_TOKENS set "MAX_TOKENS=8192"

REM ---- Host/port/timeouts ----
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8080"
if not defined BOOT_TIMEOUT set "BOOT_TIMEOUT=120"
if not defined HEALTH_TIMEOUT set "HEALTH_TIMEOUT=2"
if not defined REQUEST_TIMEOUT set "REQUEST_TIMEOUT=300"
if not defined COMPAT_RETRY_LIMIT set "COMPAT_RETRY_LIMIT=8"
if not defined MAX_REQUESTS_PER_MINUTE set "MAX_REQUESTS_PER_MINUTE=60"
if not defined SHUTDOWN_TIMEOUT set "SHUTDOWN_TIMEOUT=5"

REM ---- Runtime ----
if not defined WORKSPACE set "WORKSPACE=%~dp0workspace"
if not defined EXTRA_ARGS set "EXTRA_ARGS="
if not defined AGENTFORGE_BROWSER_HEADLESS set "AGENTFORGE_BROWSER_HEADLESS=0"
if not defined MAX_ITERATIONS set "MAX_ITERATIONS=10"
if not defined MAX_REPEATS set "MAX_REPEATS=3"
if not defined AGENT_TIMEOUT set "AGENT_TIMEOUT=300"

REM ---- Tool timeout env defaults (read by runtime/tool modules) ----
if not defined TOOL_TIMEOUT_BROWSER_NAV_MS set "TOOL_TIMEOUT_BROWSER_NAV_MS=30000"
if not defined TOOL_TIMEOUT_BROWSER_ACTION_MS set "TOOL_TIMEOUT_BROWSER_ACTION_MS=5000"
if not defined TOOL_TIMEOUT_BROWSER_WAIT_MS set "TOOL_TIMEOUT_BROWSER_WAIT_MS=10000"
if not defined TOOL_TIMEOUT_WEB_REQUEST_S set "TOOL_TIMEOUT_WEB_REQUEST_S=30"
if not defined TOOL_TIMEOUT_WEB_SEARCH_S set "TOOL_TIMEOUT_WEB_SEARCH_S=15"
if not defined TOOL_TIMEOUT_PHOTOSHOP_S set "TOOL_TIMEOUT_PHOTOSHOP_S=30"
if not defined TOOL_TIMEOUT_PROCESS_LIST_S set "TOOL_TIMEOUT_PROCESS_LIST_S=10"
if not defined SHELL_WORKSPACE_ONLY set "SHELL_WORKSPACE_ONLY=1"

if not exist "%WORKSPACE%" (
    mkdir "%WORKSPACE%" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: cannot create workspace directory: %WORKSPACE%
        goto :fail
    )
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in PATH.
    echo Install Python 3.10+ and retry.
    goto :fail
)

REM Ensure deps for first-run users (download repo then run.bat)
python -c "import rich,bs4,playwright,socketio,yaml" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: dependency installation failed.
        echo Try: python -m pip install --upgrade pip
        goto :fail
    )
)

set "RUN_ARGS="
if /I "%PROVIDER%"=="local" (
    if "%MODEL_PATH%"=="" (
        echo ERROR: MODEL_PATH is required when PROVIDER=local.
        echo Example:
        echo   set MODEL_PATH=D:\models\your-model.gguf
        echo   run.bat
        goto :fail
    )
    if not exist "%SERVER_EXE%" (
        echo ERROR: llama-server.exe not found: %SERVER_EXE%
        goto :fail
    )
    if not exist "%MODEL_PATH%" (
        echo ERROR: model file not found: %MODEL_PATH%
        goto :fail
    )
    set "RUN_ARGS=run \"%MODEL_PATH%\" --provider local --server-exe \"%SERVER_EXE%\""
) else if /I "%PROVIDER%"=="openai_compatible" (
    if "%BASE_URL%"=="" (
        echo ERROR: BASE_URL is required in openai_compatible mode.
        goto :fail
    )
    if "%MODEL_ID%"=="" (
        echo ERROR: MODEL_ID is required in openai_compatible mode.
        goto :fail
    )
    set "RUN_ARGS=run --provider openai_compatible --base-url \"%BASE_URL%\" --model-id \"%MODEL_ID%\" --api-key-env \"%API_KEY_ENV%\""
) else (
    echo ERROR: invalid PROVIDER value: "%PROVIDER%"
    echo Allowed values: local, openai_compatible
    goto :fail
)

python -m agentforge.cli %RUN_ARGS% ^
  --host "%HOST%" ^
  --ctx-size %CTX_SIZE% ^
  --gpu-layers %GPU_LAYERS% ^
  --threads %THREADS% ^
  --temp %TEMPERATURE% ^
  --top-p %TOP_P% ^
  --top-k %TOP_K% ^
  --repeat-penalty %REPEAT_PENALTY% ^
  --seed %SEED% ^
  --reasoning-format "%REASONING_FORMAT%" ^
  --reasoning-effort "%REASONING_EFFORT%" ^
  --max-tokens %MAX_TOKENS% ^
  --port %PORT% ^
  --boot-timeout %BOOT_TIMEOUT% ^
  --health-timeout %HEALTH_TIMEOUT% ^
  --request-timeout %REQUEST_TIMEOUT% ^
  --shutdown-timeout %SHUTDOWN_TIMEOUT% ^
  --compat-retry-limit %COMPAT_RETRY_LIMIT% ^
  --max-requests-per-minute %MAX_REQUESTS_PER_MINUTE% ^
  --max-iterations %MAX_ITERATIONS% ^
  --max-repeats %MAX_REPEATS% ^
  --agent-timeout %AGENT_TIMEOUT% ^
  --workspace "%WORKSPACE%" ^
  %EXTRA_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"
goto :end

:fail
set "EXIT_CODE=1"

:end
popd
exit /b %EXIT_CODE%
