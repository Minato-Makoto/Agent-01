@echo off
setlocal EnableExtensions
pushd "%~dp0"
set PYTHONPATH=%~dp0src

REM ============================================================
REM Agent-01 launcher (Windows-only, single-file).
REM Edit defaults below or override by `set VAR=value` before run.bat.
REM
REM Example 1 - Local llama.cpp:
REM   set PROVIDER=local
REM   set SERVER_EXE=D:\tools\llama-server.exe
REM   set MODEL_PATH=D:\models\my-model.gguf
REM   run.bat
REM
REM Example 2 - OpenAI-compatible remote:
REM   set PROVIDER=openai_compatible
REM   set BASE_URL=https://api.openai.com/v1
REM   set MODEL_ID=gpt-5-mini
REM   set OPENAI_API_KEY=YOUR_KEY
REM   run.bat
REM
REM Example 3 - Browser tools mở cửa sổ cho user xem:
REM   set AGENTFORGE_BROWSER_HEADLESS=0
REM   run.bat
REM ============================================================

REM Provider mode: local | openai_compatible
if not defined PROVIDER set PROVIDER=local

REM Local backend paths (dùng khi PROVIDER=local)
if not defined SERVER_EXE set SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe
if not defined MODEL_PATH set MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Qwen3VL-Thinking\Qwen3VL-8B-Thinking-Q4_K_M.gguf

REM Remote backend settings (dùng khi PROVIDER=openai_compatible)
if not defined BASE_URL set BASE_URL=http://127.0.0.1:8080
if not defined MODEL_ID set MODEL_ID=local
if not defined API_KEY_ENV set API_KEY_ENV=OPENAI_API_KEY

REM Inference tuning
if not defined CTX_SIZE set CTX_SIZE=16384
if not defined GPU_LAYERS set GPU_LAYERS=-1
if not defined THREADS set THREADS=0
if not defined TEMPERATURE set TEMPERATURE=0.1
if not defined TOP_P set TOP_P=0.9
if not defined TOP_K set TOP_K=40
if not defined REPEAT_PENALTY set REPEAT_PENALTY=1.1
if not defined SEED set SEED=-1
if not defined REASONING_FORMAT set REASONING_FORMAT=auto
if not defined REASONING_EFFORT set REASONING_EFFORT=low
if not defined MAX_TOKENS set MAX_TOKENS=8192

REM Backend host/port + timeout
if not defined HOST set HOST=127.0.0.1
if not defined PORT set PORT=8080
if not defined BOOT_TIMEOUT set BOOT_TIMEOUT=120
if not defined HEALTH_TIMEOUT set HEALTH_TIMEOUT=2
if not defined REQUEST_TIMEOUT set REQUEST_TIMEOUT=300
if not defined COMPAT_RETRY_LIMIT set COMPAT_RETRY_LIMIT=8

REM Runtime behavior
if not defined WORKSPACE set WORKSPACE=%~dp0workspace
if not defined EXTRA_ARGS set EXTRA_ARGS=
if not defined AGENTFORGE_BROWSER_HEADLESS set AGENTFORGE_BROWSER_HEADLESS=0

if not exist "%WORKSPACE%" (
    mkdir "%WORKSPACE%" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: cannot create workspace directory: %WORKSPACE%
        goto :fail
    )
)

REM Ensure deps for first-run users (download repo then run.bat)
python -c "import rich,bs4,playwright,socketio,yaml" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: dependency installation failed.
        goto :fail
    )
)

set RUN_ARGS=
if /I "%PROVIDER%"=="local" (
    if "%MODEL_PATH%"=="" (
        echo ERROR: MODEL_PATH is required in local mode.
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
    set RUN_ARGS=run "%MODEL_PATH%" --provider local --server-exe "%SERVER_EXE%"
) else if /I "%PROVIDER%"=="openai_compatible" (
    if "%BASE_URL%"=="" (
        echo ERROR: BASE_URL is required in openai_compatible mode.
        goto :fail
    )
    if "%MODEL_ID%"=="" (
        echo ERROR: MODEL_ID is required in openai_compatible mode.
        goto :fail
    )
    set RUN_ARGS=run --provider openai_compatible --base-url "%BASE_URL%" --model-id "%MODEL_ID%" --api-key-env "%API_KEY_ENV%"
) else (
    echo ERROR: invalid PROVIDER value: "%PROVIDER%"
    echo Allowed: local, openai_compatible
    goto :fail
)

python -m agentforge.cli %RUN_ARGS% --host "%HOST%" --ctx-size %CTX_SIZE% --gpu-layers %GPU_LAYERS% --threads %THREADS% --temp %TEMPERATURE% --top-p %TOP_P% --top-k %TOP_K% --repeat-penalty %REPEAT_PENALTY% --seed %SEED% --reasoning-format "%REASONING_FORMAT%" --reasoning-effort "%REASONING_EFFORT%" --max-tokens %MAX_TOKENS% --port %PORT% --boot-timeout %BOOT_TIMEOUT% --health-timeout %HEALTH_TIMEOUT% --request-timeout %REQUEST_TIMEOUT% --compat-retry-limit %COMPAT_RETRY_LIMIT% --workspace "%WORKSPACE%" %EXTRA_ARGS%
set EXIT_CODE=%ERRORLEVEL%
goto :end

:fail
set EXIT_CODE=1

:end
popd
exit /b %EXIT_CODE%
