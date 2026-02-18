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
REM     REM co the dat MODEL_PATH="D:\models\my-model.gguf"
REM     run.bat
REM
REM   Remote:
REM     set PROVIDER=openai_compatible
REM     set BASE_URL=https://api.openai.com/v1
REM     set MODEL_ID=gpt-5-mini
REM     set OPENAI_API_KEY=YOUR_KEY
REM     run.bat
REM
REM   Local (performance profile):
REM     set CTX_SIZE=8192
REM     set GPU_LAYERS=20
REM     set THREADS=8
REM     set MAX_TOKENS=2048
REM     run.bat
REM
REM   Safe shell mode (default):
REM     set SHELL_WORKSPACE_ONLY=1
REM     run.bat
REM
REM Parameter guide (y nghia + tac dong + vi du):
REM   PROVIDER (-> --provider):
REM     local  = tu mo llama-server trong may.
REM     openai_compatible = goi endpoint san co qua BASE_URL.
REM     Vi du: set PROVIDER=openai_compatible -> khong can MODEL_PATH.
REM
REM   MODEL_PATH / SERVER_EXE:
REM     MODEL_PATH la file .gguf se duoc nap.
REM     Vi du: MODEL_PATH rong => fail-fast ngay, khong vao runtime.
REM
REM   CTX_SIZE:
REM     Tang CTX_SIZE -> giu duoc lich su dai hon, ton RAM/VRAM hon.
REM     Vi du: 8192 nhanh hon, 16384 giu context tot hon.
REM
REM   TEMPERATURE + TOP_P + TOP_K:
REM     Temperature thap -> output on dinh, cao -> da dang nhung de lang man.
REM     Vi du: TEMP=0.1 cho coding on dinh; TEMP=0.7 cho brainstorming.
REM
REM   MAX_TOKENS:
REM     Tran do dai cau tra loi moi lan model sinh.
REM     Vi du: 2048 tranh output qua dai; 8192 cho task can giai thich dai.
REM
REM   BOOT_TIMEOUT / REQUEST_TIMEOUT / SHUTDOWN_TIMEOUT:
REM     BOOT_TIMEOUT: cho local server khoi dong.
REM     REQUEST_TIMEOUT: gioi han 1 request den model.
REM     SHUTDOWN_TIMEOUT: cho local process tat em truoc khi kill.
REM     Vi du: model lon khoi dong cham -> tang BOOT_TIMEOUT 120 -> 240.
REM
REM   MAX_REQUESTS_PER_MINUTE:
REM     Gioi han request de tranh runaway loop dot credit.
REM     Vi du: dat 30 khi debug, 60 cho run thuong.
REM
REM   MAX_ITERATIONS / MAX_REPEATS / AGENT_TIMEOUT:
REM     Guard rail cho vong tool loop.
REM     Vi du: MAX_ITERATIONS=5 -> dung som neu model goi tool qua nhieu.
REM
REM   TOOL_TIMEOUT_*:
REM     Timeout rieng cho tung nhom tool browser/web/photoshop/process_list.
REM     Vi du: web cham -> tang TOOL_TIMEOUT_WEB_REQUEST_S=60.
REM
REM   SHELL_WORKSPACE_ONLY:
REM     1 = shell_command chi cho chay trong WORKSPACE (an toan, mac dinh).
REM     0 = cho phep cwd ben ngoai workspace (it an toan hon).
REM
REM   AGENTFORGE_BROWSER_HEADLESS:
REM     0 = mo browser de user xem; 1 = chay an.
REM
REM   EXTRA_ARGS:
REM     Truyen them flag raw vao `agentforge run`.
REM     Vi du: set EXTRA_ARGS=--help
REM ============================================================

REM ---- Provider mode ----
if not defined PROVIDER set "PROVIDER=local"

REM ---- Local backend (required when PROVIDER=local) ----
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Qwen3VL-Thinking\Qwen3VL-8B-Thinking-Q4_K_M.gguf"

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

REM Normalize quoted env inputs (support both: set VAR=value and set VAR="value")
set "PROVIDER=%PROVIDER:"=%"
set "SERVER_EXE=%SERVER_EXE:"=%"
set "MODEL_PATH=%MODEL_PATH:"=%"
set "BASE_URL=%BASE_URL:"=%"
set "MODEL_ID=%MODEL_ID:"=%"
set "API_KEY_ENV=%API_KEY_ENV:"=%"
set "WORKSPACE=%WORKSPACE:"=%"

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
    goto :run_local
) else if /I "%PROVIDER%"=="openai_compatible" (
    if "%BASE_URL%"=="" (
        echo ERROR: BASE_URL is required in openai_compatible mode.
        goto :fail
    )
    if "%MODEL_ID%"=="" (
        echo ERROR: MODEL_ID is required in openai_compatible mode.
        goto :fail
    )
    goto :run_remote
) else (
    echo ERROR: invalid PROVIDER value: "%PROVIDER%"
    echo Allowed values: local, openai_compatible
    goto :fail
)

:run_local
python -m agentforge.cli run "%MODEL_PATH%" --provider local --server-exe "%SERVER_EXE%" ^
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

:run_remote
python -m agentforge.cli run --provider openai_compatible --base-url "%BASE_URL%" --model-id "%MODEL_ID%" --api-key-env "%API_KEY_ENV%" ^
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
