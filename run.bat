@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 (
    echo ERROR: cannot access repository directory.
    exit /b 1
)
set "PYTHONPATH=%~dp0src"

REM ============================================================
REM Tập lệnh Khởi chạy Agent-01 (Dành riêng cho Windows)
REM
REM [>] HƯỚNG DẪN KHỞI CHẠY NHANH
REM ------------------------------------------------------------
REM 1) Chế độ Cục bộ (Mặc định):
REM    Đảm bảo đường dẫn biến MODEL_PATH và SERVER_EXE trỏ đến các tập tin hợp lệ.
REM    Chạy lệnh: run.bat
REM
REM 2) Chế độ Từ xa (Tương thích API OpenAI):
REM    set PROVIDER=openai_compatible
REM    set BASE_URL=https://api.openai.com/v1
REM    set MODEL_ID=gpt-4o
REM    set OPENAI_API_KEY=YOUR_KEY
REM    run.bat
REM
REM 3) Chế độ An toàn (Môi trường cách ly hộp cát):
REM    set SHELL_WORKSPACE_ONLY=1
REM    run.bat
REM
REM [i] HƯỚNG DẪN CẤU HÌNH THÔNG SỐ
REM ------------------------------------------------------------
REM Người dùng có thể chỉnh sửa các giá trị mặc định trực tiếp bên dưới 
REM tại các dòng "set VAR=value", hoặc ghi đè tạm thời thông qua môi trường dòng lệnh trước khi chạy:
REM   set MAX_TOKENS=4096 && run.bat
REM ============================================================

REM ---- 1. Hệ thống & Chế độ Vận hành (Provider Mode) ----

REM [PROVIDER]
REM Khái niệm: Xác định bộ mã nguồn xử lý và quản lý mô hình ngôn ngữ lớn (LLM).
REM Ảnh hưởng: Giá trị 'local' sẽ gọi tệp thực thi llama-server.exe trên máy. Giá trị 'openai_compatible' sẽ tạo kết nối định tuyến API đến máy chủ bên ngoài.
REM Cú pháp ví dụ: set PROVIDER=local (Sử dụng cấu hình máy tính cá nhân).
if not defined PROVIDER set "PROVIDER=local"

REM ---- 2. Cấu hình Máy chủ Cục bộ (Kích hoạt với PROVIDER=local) ----

REM [SERVER_EXE] & [MODEL_PATH]
REM Khái niệm: Đường dẫn lưu trữ thư mục tuyệt đối đến phần mềm llama-server và tập tin cơ sở dữ liệu mô hình (GGUF).
REM Ảnh hưởng: Bắt buộc cung cấp để khởi động dịch vụ máy chủ cục bộ. Vắng thông số MODEL_PATH, phần mềm sẽ dừng khởi động kèm thông báo lỗi thiếu bộ nhớ mô hình.
REM Cú pháp ví dụ: set MODEL_PATH="D:\models\Llama-3.gguf"
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Llama-3.3-8B-Instruct.Q4_K_M.gguf"

REM ---- 3. Cấu hình Máy chủ Từ xa (Kích hoạt với PROVIDER=openai_compatible) ----

REM [BASE_URL], [MODEL_ID], [API_KEY_ENV]
REM Khái niệm: Thiết lập mạng kết nối đến đường dẫn API máy chủ bên thứ ba. API_KEY_ENV chỉ định tên biến lưu trữ khóa xác thực dạng mã hóa.
REM Ảnh hưởng: Bắt buộc cấu hình thông số BASE_URL và thiết lập rõ MODEL_ID. Việc thiếu khóa API (API Key) từ hệ thống gây ra lỗi hệ thống từ chối kết nối giao thức.
REM Cú pháp ví dụ: set BASE_URL=https://api.openai.com/v1, set MODEL_ID=gpt-4o
if not defined BASE_URL set "BASE_URL=http://127.0.0.1:8080"
if not defined MODEL_ID set "MODEL_ID=local"
if not defined API_KEY_ENV set "API_KEY_ENV=OPENAI_API_KEY"

REM ---- 4. Tùy chỉnh Suy luận (Inference Tuning) ----

REM [CTX_SIZE]
REM Khái niệm: Tổng kích thước vùng nhớ đệm ngữ cảnh (tính theo đơn vị token) được cấp phát hoạt động cho phiên làm việc hiện tại.
REM Ảnh hưởng: Giá trị CTX_SIZE cao cho phép phần mềm phân tích tệp tin dài hạn, nhưng tiêu tốn mạnh bộ nhớ dung lượng cao của VRAM và RAM.
REM Cú pháp ví dụ: 8192 (Phản hồi tốc độ cao), 16384 (Xử lý tập tin chuỗi đồ sộ).
if not defined CTX_SIZE set "CTX_SIZE=16384"

REM [GPU_LAYERS] & [THREADS]
REM Khái niệm: Phân bổ số lượng xử lý tính toán của lớp nơ-ron lên bộ vi xử lý thẻ đồ họa GPU (-1 = đẩy toàn bộ dải băng) và cấp độ nhận luồng vi xử lý ở CPU (0 = phân bổ tự động tự động hóa).
REM Ảnh hưởng: Thao tác thay đổi GPU_LAYERS giúp tối đa hóa tốc độ nạp dữ liệu chuỗi (token generation). THREADS dùng để phân luồng lại hiệu năng vận hành cho CPU.
if not defined GPU_LAYERS set "GPU_LAYERS=-1"
if not defined THREADS set "THREADS=0"

REM [TEMPERATURE]
REM Khái niệm: Tỷ lệ phân kỳ phân phối dữ liệu cho ra văn bản (entropy).
REM Ảnh hưởng: Giá trị hệ số (0.1) xuất thông số mang cấu trúc chính xác, rập khuôn, thích hợp môi trường phân tích mã độc lập. Mức hệ số (0.7) phù hợp với những dự án văn bản lên dạng thiết kế dự thảo ý tưởng.
if not defined TEMPERATURE set "TEMPERATURE=0.1"

REM [TOP_P]
REM Khái niệm: Hệ số chọn mẫu cắt bỏ theo định dạng xác suất cộng dồn (Nucleus sampling).
REM Ảnh hưởng: Tự động loại bỏ các token mang giá trị xác suất không đáng kể. Ứng dụng xuất văn bản bớt loạn mà không mang nguy cơ giống với hệ số Temperature.
if not defined TOP_P set "TOP_P=0.9"

REM [TOP_K]
REM Khái niệm: Giới hạn tập số lựa chọn mã hóa xuống cho số K mã hiển thị.
REM Ảnh hưởng: Khống chế thuật toán tạo ra lỗi chữ văn bản trong lúc nâng mức thông số biến Temperature (độ ngẫu nhiên văn bản).
if not defined TOP_K set "TOP_K=40"

REM [REPEAT_PENALTY]
REM Khái niệm: Số định mức trừ phạt nhằm cấm lặp lại nội dung đã phản hồi.
REM Ảnh hưởng: Các cấu trúc tăng trên mức 1.0 cho văn bản LLM tránh tình huống hiện tượng dính vào lỗi vòng lặp text lặp vô thời hạn (infinite loop text). Cấu trúc 1.1 đến dạng 1.2 đáp ứng cho mô hình ổn định nhất.
if not defined REPEAT_PENALTY set "REPEAT_PENALTY=1.1"

REM [SEED] & [REASONING_EFFORT]
REM Khái niệm: Giá trị SEED khóa giá trị ngẫu nhiên gốc sinh hàm (-1 = off). Thông số REASONING_EFFORT (Chi phí phân rã vấn đề logic suy luận chuyên sâu) trên dòng model có thông số (o1, o3).
REM Ảnh hưởng: Chỉ số khóa thuật bằng giá trị SEED cho ra chính xác cấu hồi output hỗ trợ cho quy trình sửa và gỡ lỗi (Debugging).
if not defined SEED set "SEED=-1"
if not defined REASONING_EFFORT set "REASONING_EFFORT=low"

REM [MAX_TOKENS]
REM Khái niệm: Giới hạn mức độ phần mềm tải giới hạn trả thông điệp sinh.
REM Ảnh hưởng: Giảm khả năng LLM tạo văn bản quá khổ dài. Mức chuẩn thiết lập 8192 để không tạo cúp máy file đang chạy in output.
if not defined MAX_TOKENS set "MAX_TOKENS=8192"

REM ---- 5. Dấu thời gian phản hồi máy chủ & Lệnh Mạng ----

REM [HOST] & [PORT]
REM Khái niệm: Điểm kết nối giao thức địa chỉ IPv4/IPv6 qua Port dịch vụ.
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8080"

REM [BOOT_TIMEOUT], [REQUEST_TIMEOUT], [HEALTH_TIMEOUT], [SHUTDOWN_TIMEOUT]
REM Khái niệm: Vòng lặp ngưỡng giây chờ phần mềm xử lý gọi khởi chạy máy chủ, trả request gửi (API), kiểm tra gói (ping) truy và quá trình thoát quy trình một cách chuẩn thao tác.
REM Ảnh hưởng: Với tệp LLM nặng tải RAM trên cấu kiện ổ thiết bị thường bằng cơ cứng (HDD) khuyến nghị chỉnh BOOT_TIMEOUT tăng lên hệ 240+ tránh văng phần mềm.
if not defined BOOT_TIMEOUT set "BOOT_TIMEOUT=120"
if not defined HEALTH_TIMEOUT set "HEALTH_TIMEOUT=2"
if not defined REQUEST_TIMEOUT set "REQUEST_TIMEOUT=300"
if not defined SHUTDOWN_TIMEOUT set "SHUTDOWN_TIMEOUT=5"

REM [COMPAT_RETRY_LIMIT] & [MAX_REQUESTS_PER_MINUTE]
REM Khái niệm: Thông số chặn cố định về lần gửi lỗi API gửi bị đóng mạng và max truy lặp 1 phút.
REM Ảnh hưởng: Cầu chì bảo vệ tài khoản nạp tín dụng qua dịch vụ giới hạn các query từ vòng tròn xử lý gọi truy suất vô ngắt quãng.
if not defined COMPAT_RETRY_LIMIT set "COMPAT_RETRY_LIMIT=8"
if not defined MAX_REQUESTS_PER_MINUTE set "MAX_REQUESTS_PER_MINUTE=60"

REM ---- 6. Thông số ngắt bộ khung phần mềm Agent ----

REM [MAX_ITERATIONS], [MAX_REPEATS], [AGENT_TIMEOUT]
REM Khái niệm: Chuỗi kỹ thuật định tuyến cho quá trình AI không chạy ngắt (Infinite). Khống bộ xử lý truy vòng lập vô ích qua số lần cho phép vòng lật (MAX_ITERATIONS). Số lần dùng công cụ trượt liên lục bởi tool gọi tool giống kết (MAX_REPEATS) cùng dải định độ ngõ ra (AGENT_TIMEOUT).
REM Ảnh hưởng: Đưa hệ thống vào mạch chốt bảo vệ đóng ngay tài nguyên khi bộ khung logic phần mềm không vượt lỗi code ngỏ.
if not defined MAX_ITERATIONS set "MAX_ITERATIONS=25"
if not defined MAX_REPEATS set "MAX_REPEATS=3"
if not defined AGENT_TIMEOUT set "AGENT_TIMEOUT=300"

REM ---- 7. Thiết lập bổ sung tập Công cụ ----

REM [WORKSPACE], [EXTRA_ARGS]
REM Khái niệm: Mở vùng hoạt động cho cấu hình Workspace bảo vệ và nhập mảng biến thông số (Args) ép lệnh chéo CLI.
if not defined WORKSPACE set "WORKSPACE=%~dp0workspace"
if not defined EXTRA_ARGS set "EXTRA_ARGS="

REM [AGENTFORGE_BROWSER_HEADLESS] & [AGENTFORGE_DESKTOP_CONTROL]
REM Khái niệm: Cài giá trị 0 = Cho khởi duyệt chương trình qua hiển thị tab windows xem. Bằng 1 = Hoạt động tiến trình trình duyệt ngầm xử lý (headless).
REM Ảnh hưởng: Phương diện 0 để chạy quá trình xử lý bắt lỗi cấu trúc nhưng cheo màn hình hiển cửa sổ ngắt gián đoạn thao tác màn hình làm việc (window popping).
if not defined AGENTFORGE_BROWSER_HEADLESS set "AGENTFORGE_BROWSER_HEADLESS=0"
if not defined AGENTFORGE_DESKTOP_CONTROL set "AGENTFORGE_DESKTOP_CONTROL=1"

REM [TOOL_TIMEOUT_*]
REM Khái niệm: Ngưỡng ngắt tính theo MS/S chuyên về thiết bị nhóm trình duyệt, điều khiền cửa số ứng dung photoshop/shell.
REM Ảnh hưởng: Tránh văng treo (froze lag) chương trình do mạng phản chờ duyệt không trả web hay phần mềm photoshop mất phản.
if not defined TOOL_TIMEOUT_BROWSER_NAV_MS set "TOOL_TIMEOUT_BROWSER_NAV_MS=30000"
if not defined TOOL_TIMEOUT_BROWSER_ACTION_MS set "TOOL_TIMEOUT_BROWSER_ACTION_MS=5000"
if not defined TOOL_TIMEOUT_BROWSER_WAIT_MS set "TOOL_TIMEOUT_BROWSER_WAIT_MS=10000"
if not defined TOOL_TIMEOUT_DESKTOP_ACTION_MS set "TOOL_TIMEOUT_DESKTOP_ACTION_MS=5000"
if not defined TOOL_TIMEOUT_DESKTOP_SCREENSHOT_S set "TOOL_TIMEOUT_DESKTOP_SCREENSHOT_S=15"
if not defined TOOL_TIMEOUT_WEB_REQUEST_S set "TOOL_TIMEOUT_WEB_REQUEST_S=30"
if not defined TOOL_TIMEOUT_WEB_SEARCH_S set "TOOL_TIMEOUT_WEB_SEARCH_S=15"
if not defined TOOL_TIMEOUT_PHOTOSHOP_S set "TOOL_TIMEOUT_PHOTOSHOP_S=30"
if not defined TOOL_TIMEOUT_PROCESS_LIST_S set "TOOL_TIMEOUT_PROCESS_LIST_S=10"

REM [SHELL_WORKSPACE_ONLY]
REM Khái niệm: Bộ cách ly chạy ứng dụng dạng hộp cắt ứng với trình quản hệ command prompt (Terminal).
REM Ảnh hưởng: Thao báo cấu 1/True (Mặc Định) là chỉ cho tệp tin/xoá đọc thông qua bộ lưu dữ liệu WORKSPACE. Tắt chỉ số 0 sẽ thông bộ cách hạn cấp đọc ghi từ mã code vào thẳng bất ổ cứng thiết bị nội hệ file C máy (Dành riêng cấu trúc uỷ quyền 100% PC cho Agent).
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
python -c "import rich,bs4,playwright,socketio,yaml,pyautogui" >nul 2>&1
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

:end
popd
exit /b %EXIT_CODE%
