@echo off
echo ========================================
echo  AgentForge CLI
echo ========================================
echo.
echo Default mode: LOCAL llama-server (v1.0.1)
echo.

REM ============================================================
REM  CONFIGURATION - Edit these values before running
REM  Full parameter reference: RUNTIME_PARAMETERS.md
REM ============================================================

REM Provider mode:
REM   local              -> run local llama-server + GGUF
REM   openai_compatible  -> connect to remote endpoint
set PROVIDER=local

REM Local mode only: path to llama-server.exe
set SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe

REM Local mode only: path to your GGUF model file
set MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Qwen3VL-Thinking\Qwen3VL-8B-Thinking-Q4_K_M.gguf

REM Remote mode only: endpoint + model id + api key env
set BASE_URL=http://127.0.0.1:8080
set MODEL_ID=local
set API_KEY_ENV=OPENAI_API_KEY

REM Context window size (larger = more tool rounds, more VRAM)
set CTX_SIZE=16384

REM GPU layers (-1 = all layers on GPU, 0 = CPU only)
set GPU_LAYERS=-1

REM CPU threads (0 = auto)
set THREADS=0

REM Temperature (0.0-1.0, lower = more precise)
set TEMPERATURE=0.1

REM Sampling controls
set TOP_P=0.9
set TOP_K=40
set REPEAT_PENALTY=1.1
set SEED=-1
REM For llama.cpp-style providers
set REASONING_FORMAT=auto
REM For OpenAI reasoning models (empty = disabled)
set REASONING_EFFORT=

REM Max tokens per response
set MAX_TOKENS=8192

REM Local mode network bind
set HOST=127.0.0.1
set PORT=8080

REM Runtime timeouts/retry policy
set BOOT_TIMEOUT=120
set HEALTH_TIMEOUT=2
set REQUEST_TIMEOUT=300
set COMPAT_RETRY_LIMIT=8

REM Workspace directory (relative to project root)
set WORKSPACE=%~dp0workspace

REM Extra arguments (e.g. --verbose, --session <id>)
set EXTRA_ARGS=

REM ----------------------------------------------------------------
REM Optional extras:
REM   set EXTRA_ARGS=--verbose
REM   set EXTRA_ARGS=--session <id>
REM ----------------------------------------------------------------

REM ============================================================
REM  DO NOT EDIT BELOW THIS LINE
REM ============================================================

pushd "%~dp0"
set PYTHONPATH=%~dp0src

REM Validate workspace
if not exist "%WORKSPACE%" (
    echo ERROR: Workspace directory not found!
    echo Expected: %WORKSPACE%
    echo Please run setup or create the workspace directory.
    pause
    popd
    exit /b 1
)

REM Install dependencies from requirements.txt
pip install -r requirements.txt --quiet 2>nul

REM Install Chromium for Browser skill (required - skill is in workspace)
playwright install chromium --quiet 2>nul

REM Build launch args by provider
set RUN_ARGS=
if /I "%PROVIDER%"=="local" (
    if not exist "%SERVER_EXE%" (
        echo ERROR: llama-server.exe not found!
        echo Please edit run.bat and set SERVER_EXE path.
        echo Current path: %SERVER_EXE%
        pause
        popd
        exit /b 1
    )
    if not exist "%MODEL_PATH%" (
        echo ERROR: Model file not found!
        echo Please edit run.bat and set MODEL_PATH to your .gguf file.
        echo Current path: %MODEL_PATH%
        pause
        popd
        exit /b 1
    )
    set RUN_ARGS=run "%MODEL_PATH%" --provider local --server-exe "%SERVER_EXE%"
) else (
    if /I "%PROVIDER%"=="openai_compatible" (
        if "%BASE_URL%"=="" (
            echo ERROR: BASE_URL is required in openai_compatible mode.
            pause
            popd
            exit /b 1
        )
        if "%MODEL_ID%"=="" (
            echo ERROR: MODEL_ID is required in openai_compatible mode.
            pause
            popd
            exit /b 1
        )
        set RUN_ARGS=run --provider openai_compatible --base-url "%BASE_URL%" --model-id "%MODEL_ID%" --api-key-env "%API_KEY_ENV%"
    ) else (
        echo ERROR: Invalid PROVIDER value: "%PROVIDER%"
        echo Allowed values: local, openai_compatible
        pause
        popd
        exit /b 1
    )
)

REM Launch AgentForge
python -m agentforge.cli %RUN_ARGS% --host "%HOST%" --ctx-size %CTX_SIZE% --gpu-layers %GPU_LAYERS% --threads %THREADS% --temp %TEMPERATURE% --top-p %TOP_P% --top-k %TOP_K% --repeat-penalty %REPEAT_PENALTY% --seed %SEED% --reasoning-format "%REASONING_FORMAT%" --reasoning-effort "%REASONING_EFFORT%" --max-tokens %MAX_TOKENS% --port %PORT% --boot-timeout %BOOT_TIMEOUT% --health-timeout %HEALTH_TIMEOUT% --request-timeout %REQUEST_TIMEOUT% --compat-retry-limit %COMPAT_RETRY_LIMIT% --workspace "%WORKSPACE%" %EXTRA_ARGS%

popd
pause
