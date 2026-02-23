@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 (
    echo ERROR: không thể truy cập thư mục repository.
    exit /b 1
)
set "PYTHONPATH=%~dp0src"

REM Local overrides (không commit): có thể đặt MODEL_PATH/API key tại run.local.bat
if exist "%~dp0run.local.bat" (
    call "%~dp0run.local.bat"
)

REM ============================================================
REM Trình khởi chạy Agent-01 (Windows)

REM ---- 1) Provider ----

REM - PROVIDER=local: chạy model GGUF trên máy (cần SERVER_EXE + MODEL_PATH)
REM - PROVIDER=openai_compatible: gọi model qua API (cần BASE_URL + MODEL_ID)
if not defined PROVIDER set "PROVIDER=local"

REM ---- 2) Cấu hình offline (chỉ dùng khi PROVIDER=local) ----

REM BASE_URL:
REM - URL cho llama-server, mặc định: http://127.0.0.1:8080
REM
REM SERVER_EXE:
REM - Đường dẫn đến llama-server.exe.
REM
REM MODEL_PATH:
REM - Đường dẫn đến model .gguf.
REM Ví dụ:
REM   set "MODEL_PATH=D:\Models\Qwen.gguf"
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-server\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH=C:\models\your-model.gguf"

REM ---- 3) Cấu hình online (chỉ dùng khi PROVIDER=openai_compatible) ----

REM BASE_URL:
REM - Địa chỉ endpoint chat-completions compatible.
REM - Thường có dạng: https://host/v1
REM
REM MODEL_ID:
REM - Định danh/ tên model mà nhà cung cấp yêu cầu.
REM
REM API_KEY_ENV:
REM - Tên biến môi trường chứa API key (không phải giá trị key).
REM - Mặc định: OPENAI_API_KEY
REM - Xem thêm cách setup API ENV trong docs/TUTORIAL_EN.md/TUTORIAL_VI.md
if not defined BASE_URL set "BASE_URL=http://127.0.0.1:8080"
if not defined MODEL_ID set "MODEL_ID=local"
if not defined API_KEY_ENV set "API_KEY_ENV=OPENAI_API_KEY"

REM ---- 4) Tinh chỉnh inference ----

REM [CTX_SIZE]
REM Kích thước context window (token). Tăng lên để nhớ được nhiều hơn,
REM nhưng sẽ tốn RAM/VRAM hơn.
if not defined CTX_SIZE set "CTX_SIZE=16384"

REM [GPU_LAYERS] & [THREADS]
REM GPU_LAYERS=-1: đẩy tối đa qua GPU (nếu local backend hỗ trợ).
REM THREADS=0: để hệ thống tự chọn số lượng CPU thread.
if not defined GPU_LAYERS set "GPU_LAYERS=-1"
if not defined THREADS set "THREADS=0"

REM [TEMPERATURE]
REM Độ "ngẫu nhiên/sáng tạo" của output.
REM - thấp (0.1): ổn định, hợp code/phân tích.
REM - cao (0.7+): đa dạng hơn nhưng dễ lệch hơn.
if not defined TEMPERATURE set "TEMPERATURE=0.1"

REM [TOP_P]
REM Nucleus sampling. Thường để 0.9.
if not defined TOP_P set "TOP_P=0.9"

REM [TOP_K]
REM Giới hạn tập token được xem mỗi bước. Thường để 40.
if not defined TOP_K set "TOP_K=40"

REM [REPEAT_PENALTY]
REM Phạt lặp token. Thường để 1.1.
if not defined REPEAT_PENALTY set "REPEAT_PENALTY=1.1"

REM [SEED] & [REASONING_EFFORT]
REM - SEED=-1: ngẫu nhiên mỗi lần. Đặt số cụ thể nếu cần tái lập kết quả.
REM - REASONING_EFFORT: low|medium|high|extra_high (nếu backend/model hỗ trợ).
if not defined SEED set "SEED=-1"
if not defined REASONING_EFFORT set "REASONING_EFFORT=low"

REM [MAX_TOKENS]
REM Giới hạn độ dài tối đa mỗi lần model trả lời.
if not defined MAX_TOKENS set "MAX_TOKENS=8192"

REM ---- 5) Network + timeout ----

REM [HOST] & [PORT]
REM Địa chỉ/port của llama-server local.
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8080"

REM [BOOT_TIMEOUT], [REQUEST_TIMEOUT], [HEALTH_TIMEOUT], [SHUTDOWN_TIMEOUT]
REM Các ngưỡng timeout tính theo giây:
REM - BOOT_TIMEOUT: chờ server local khởi động.
REM - HEALTH_TIMEOUT: timeout từng lần health check.
REM - REQUEST_TIMEOUT: timeout mỗi request model.
REM - SHUTDOWN_TIMEOUT: chờ local process tắt.
if not defined BOOT_TIMEOUT set "BOOT_TIMEOUT=120"
if not defined HEALTH_TIMEOUT set "HEALTH_TIMEOUT=2"
if not defined REQUEST_TIMEOUT set "REQUEST_TIMEOUT=300"
if not defined SHUTDOWN_TIMEOUT set "SHUTDOWN_TIMEOUT=5"

REM [COMPAT_RETRY_LIMIT] & [MAX_REQUESTS_PER_MINUTE]
REM - COMPAT_RETRY_LIMIT: số lần thử lại khi provider không hợp payload.
REM - MAX_REQUESTS_PER_MINUTE: chặn request storm.
if not defined COMPAT_RETRY_LIMIT set "COMPAT_RETRY_LIMIT=8"
if not defined MAX_REQUESTS_PER_MINUTE set "MAX_REQUESTS_PER_MINUTE=60"

REM ---- 6) An toàn vòng lặp agent ----

REM [MAX_ITERATIONS], [MAX_REPEATS], [AGENT_TIMEOUT]
REM - MAX_ITERATIONS: giới hạn số vòng tool-call mỗi turn.
REM - MAX_REPEATS: giới hạn lặp tool với cùng argument.
REM - AGENT_TIMEOUT: timeout tổng mỗi turn (giây).
if not defined MAX_ITERATIONS set "MAX_ITERATIONS=60"
if not defined MAX_REPEATS set "MAX_REPEATS=3"
if not defined AGENT_TIMEOUT set "AGENT_TIMEOUT=300"

REM ---- 7) Workspace + tools ----

REM [WORKSPACE], [EXTRA_ARGS]
REM - WORKSPACE: thư mục làm việc của Agent.
REM - EXTRA_ARGS: truyền thêm tham số vào CLI.
if not defined WORKSPACE set "WORKSPACE=%~dp0workspace"
if not defined EXTRA_ARGS set "EXTRA_ARGS="

REM [AGENTFORGE_BROWSER_HEADLESS] & [AGENTFORGE_DESKTOP_CONTROL]
REM - AGENTFORGE_BROWSER_HEADLESS=0: mở browser để xem.
REM - AGENTFORGE_BROWSER_HEADLESS=1: chạy ẩn.
REM - AGENTFORGE_DESKTOP_CONTROL=1: bật desktop tools (chuột/bàn phím/screenshot).
if not defined AGENTFORGE_BROWSER_HEADLESS set "AGENTFORGE_BROWSER_HEADLESS=0"
if not defined AGENTFORGE_DESKTOP_CONTROL set "AGENTFORGE_DESKTOP_CONTROL=1"

REM [TOOL_TIMEOUT_*]
REM Timeout riêng cho từng nhóm tool (ms/s):
REM browser, desktop, web, photoshop, process_list.
if not defined TOOL_TIMEOUT_BROWSER_NAV_MS set "TOOL_TIMEOUT_BROWSER_NAV_MS=60000"
if not defined TOOL_TIMEOUT_BROWSER_ACTION_MS set "TOOL_TIMEOUT_BROWSER_ACTION_MS=15000"
if not defined TOOL_TIMEOUT_BROWSER_WAIT_MS set "TOOL_TIMEOUT_BROWSER_WAIT_MS=30000"
if not defined TOOL_TIMEOUT_DESKTOP_ACTION_MS set "TOOL_TIMEOUT_DESKTOP_ACTION_MS=5000"
if not defined TOOL_TIMEOUT_DESKTOP_SCREENSHOT_S set "TOOL_TIMEOUT_DESKTOP_SCREENSHOT_S=15"
if not defined TOOL_TIMEOUT_WEB_REQUEST_S set "TOOL_TIMEOUT_WEB_REQUEST_S=30"
if not defined TOOL_TIMEOUT_WEB_SEARCH_S set "TOOL_TIMEOUT_WEB_SEARCH_S=15"
if not defined TOOL_TIMEOUT_PHOTOSHOP_S set "TOOL_TIMEOUT_PHOTOSHOP_S=30"
if not defined TOOL_TIMEOUT_PROCESS_LIST_S set "TOOL_TIMEOUT_PROCESS_LIST_S=10"

REM [SHELL_WORKSPACE_ONLY]
REM - SHELL_WORKSPACE_ONLY=1: shell tool chỉ được chạy trong workspace.
REM - SHELL_WORKSPACE_ONLY=0: mở khóa (nguy hiểm, chỉ dùng khi bạn kiểm soát được).
if not defined SHELL_WORKSPACE_ONLY set "SHELL_WORKSPACE_ONLY=1"

REM Chuẩn hóa biến môi trường (hỗ trợ cả 2 kiểu: set VAR=value và set VAR="value")
set "PROVIDER=%PROVIDER:"=%"
set "SERVER_EXE=%SERVER_EXE:"=%"
if defined MODEL_PATH set "MODEL_PATH=%MODEL_PATH:"=%"
set "BASE_URL=%BASE_URL:"=%"
set "MODEL_ID=%MODEL_ID:"=%"
set "API_KEY_ENV=%API_KEY_ENV:"=%"
set "WORKSPACE=%WORKSPACE:"=%"

if not exist "%WORKSPACE%" (
    mkdir "%WORKSPACE%" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: không tạo được thư mục workspace: %WORKSPACE%
        goto :fail
    )
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: chưa tìm thấy Python trong PATH.
    echo Hãy cài Python 3.10+ rồi chạy lại.
    goto :fail
)

REM Tự động cài Python packages nếu máy chưa có đầy đủ.
python -c "import rich,bs4,playwright,socketio,yaml,pyautogui" >nul 2>&1
if errorlevel 1 (
    echo Đang cài thư viện Python từ requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: cài dependencies thất bại.
        echo Thử: python -m pip install --upgrade pip
        goto :fail
    )
)

REM Tự động cài Chromium runtime cho Playwright (best effort).
REM Nếu bước này fail, core vẫn chạy được, nhưng browser tools có thể lỗi.
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo Đang cài Playwright Chromium runtime...
    python -m playwright install chromium >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Không thể tự động cài Playwright Chromium runtime.
        echo WARNING: Browser tool có thể lỗi đến khi bạn chạy:
        echo WARNING:   python -m playwright install chromium
    )
)

if /I "%PROVIDER%"=="local" (
    if "%MODEL_PATH%"=="" (
        echo ERROR: MODEL_PATH là bắt buộc khi PROVIDER=local.
        echo Ví dụ:
        echo   set MODEL_PATH=D:\models\your-model.gguf
        echo   run.bat
        goto :fail
    )
    if not exist "%SERVER_EXE%" (
        echo ERROR: không tìm thấy llama-server.exe: %SERVER_EXE%
        goto :fail
    )
    if not exist "%MODEL_PATH%" (
        echo ERROR: không tìm thấy file model: %MODEL_PATH%
        goto :fail
    )
    goto :run_local
) else if /I "%PROVIDER%"=="openai_compatible" (
    if "%BASE_URL%"=="" (
        echo ERROR: BASE_URL là bắt buộc ở chế độ openai_compatible.
        goto :fail
    )
    if "%MODEL_ID%"=="" (
        echo ERROR: MODEL_ID là bắt buộc ở chế độ openai_compatible.
        goto :fail
    )
    goto :run_remote
) else (
    echo ERROR: giá trị PROVIDER không hợp lệ: "%PROVIDER%"
    echo Giá trị hợp lệ: local, openai_compatible
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
if not defined CI (
    if /I not "%AGENTFORGE_NO_PAUSE_ON_FAIL%"=="1" (
        echo.
        echo Failed to start Agent-01. Press any key to close the window...
        pause >nul
    )
)

:end
popd
exit /b %EXIT_CODE%
