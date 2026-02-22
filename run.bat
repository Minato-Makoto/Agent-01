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
REM 2) Chế độ Từ xa (Mượn API bên ngoài):
REM    set PROVIDER=openai_compatible
REM    set BASE_URL=https://api.openai.com/v1
REM    set MODEL_ID=gpt-4o
REM    set OPENAI_API_KEY=YOUR_KEY
REM    run.bat
REM
REM 3) Chế độ An toàn (Khóa quyền sửa file máy tính):
REM    set SHELL_WORKSPACE_ONLY=1
REM    run.bat
REM
REM [i] HƯỚNG DẪN CẤU HÌNH THÔNG SỐ
REM ------------------------------------------------------------
REM Bạn có thể đổi vĩnh viễn các thông số bằng cách sửa số đằng sau dấu "=" ở dưới.
REM Hoặc đổi tạm thời dùng ngay ở Terminal:
REM   set MAX_TOKENS=4096 && run.bat
REM ============================================================

REM ---- 1. Hệ thống & Chế độ Vận hành (Provider Mode) ----

REM [PROVIDER]
REM Khái niệm: Công tắc chọn "nơi" AI sẽ suy luận.
REM Tác động: Quyết định việc AI dùng sức mạnh phần cứng máy tính bạn (local) hay thông qua sức mạnh mạng API của dịch vụ đám mây (openai_compatible).
REM Ví dụ:
REM - PROVIDER=local (Mặc định): An toàn, riêng tư 100%, có thể rút mạng máy tính AI vẫn chạy.
REM - PROVIDER=openai_compatible: Mượn năng lực tính toán cực lớn của OpenAI máy chủ.
if not defined PROVIDER set "PROVIDER=local"

REM ---- 2. Cấu hình Máy chủ Cục bộ (Kích khoản khi PROVIDER=local) ----

REM [SERVER_EXE] & [MODEL_PATH]
REM Khái niệm: Đường dẫn tới ứng dụng khởi động AI (SERVER_EXE) và file bộ não AI (MODEL_PATH - định dạng file là .gguf).
REM Tác động: Nếu không trỏ vào đúng đường dẫn MODEL_PATH, phần mềm sẽ không thể khởi động vì "không có bộ não".
REM Ví dụ:
REM - MODEL_PATH="D:\Models\AI_Llama.gguf"
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Qwen3VL-Instruct\Qwen3VL-4B-Instruct-Q4_K_M.gguf"

REM ---- 3. Cấu hình Máy chủ Từ xa (Kích hoạt khi PROVIDER=openai_compatible) ----

REM [BASE_URL], [MODEL_ID], [API_KEY_ENV]
REM Khái niệm: Dành cho khi bạn kết nối tới máy chủ ngoài. API_KEY_ENV là tên biến môi trường chứa pass giải mã khóa tài khoản bạn.
REM Tác động: Nếu nhập thiếu BASE_URL hoặc quên khai báo API key, máy chủ sẽ chặn yêu cầu dẫn đến báo lỗi đỏ lòm.
if not defined BASE_URL set "BASE_URL=http://127.0.0.1:8080"
if not defined MODEL_ID set "MODEL_ID=local"
if not defined API_KEY_ENV set "API_KEY_ENV=OPENAI_API_KEY"

REM ---- 4. Tùy chỉnh Não Phản hồi (Inference Tuning) - MỤC QUAN TRỌNG NHẤT ----

REM [CTX_SIZE] (Kích thước: 1024, 2048, 4096, 8192, 16384...)
REM Khái niệm: Kích thước bộ nhớ "ngắn hạn" của AI. Số lượng chữ tối đa mà AI được phép ghi nhớ trong một phiên trò chuyện (hay tính bằng Token).
REM Tác động: Số lượng càng cao, AI càng nhớ được nhiều log cũ, đọc được file tài liệu dài. NHƯNG nó sẽ nuốt rất nhiều RAM / Card màn hình (VRAM).
REM Ví dụ:
REM - CTX_SIZE=8192: Đủ bộ nhớ đọc 1-2 file Word nhỏ, thích hợp Card đồ họa phổ thông.
REM - CTX_SIZE=16384: Dành cho việc ép AI nhét một dự án to vào đầu để đọc. Nếu VRAM (Card đồ họa) dưới 12GB có thể lỗi đen màn.
if not defined CTX_SIZE set "CTX_SIZE=16384"

REM [GPU_LAYERS] & [THREADS]
REM Khái niệm: Phân bổ điện toán phần cứng.
REM - GPU_LAYERS là ép bao nhiêu lớp não của AI chạy qua card Màn Hình (VRAM).
REM - THREADS là số lõi của vi xử lý (CPU) cho phép trợ lực hệ thống.
REM Tác động: Quyết định AI nhả chữ nhanh hay chậm. Giải phóng tối đa phần cứng.
REM Ví dụ: 
REM - GPU_LAYERS=-1 (Mặc định): Đẩy 100% mạng AI qua Card màn hình (Nhả chữ nhanh nhất thị trường). Nếu máy quá giựt/văng thì có thể tự hạ xuống sửa số bằng 30 hoặc 20.
REM - THREADS=0 (Mặc định): Để máy tự động quyết định CPU rảnh bao nhiêu thì xài bấy nhiêu.
if not defined GPU_LAYERS set "GPU_LAYERS=-1"
if not defined THREADS set "THREADS=0"

REM [TEMPERATURE] (Khoảng giá trị: 0.0 đến 2.0)
REM Khái niệm: Độ "sáng tạo", hoặc "ngẫu hứng" khi lấy từ của AI.
REM Tác động: Càng thấp thì văn càng nguyên tắc, kỹ thuật. Càng cao thì AI càng dùng từ bay bổng, bất ngờ, dễ bị ảo giác chế lời điêu toa.
REM Ví dụ:
REM - TEMPERATURE=0.1 (Mặc định): Chuyên cho việc code, sửa logic phần mềm. AI không "vẽ râu ria", trả lời khô khan nhưng trúng thứ cần tìm.
REM - TEMPERATURE=0.8: Viết email, viết nội dung cho trang Facebook. Cần sự mở rộng từ điển cao nhất để nghe giống người thật.
if not defined TEMPERATURE set "TEMPERATURE=0.1"

REM [TOP_P] (Khoảng giá trị: 0.0 đến 1.0)
REM Khái niệm: Màng lọc tỷ lệ % từ khóa. AI sẽ sắp xếp các từ tiếp theo có khả năng được nó chọn từ tốt nhất (VD: từ "Tôi" là 80%, "Tớ" là 10%) dần xuống thấp. TOP_P sẽ lấy từ cao nhất xuống tới khi ĐỦ tổng tỷ lệ P. Phần từ rác ở dưới đáy bảng sẽ bị gạch bỏ hoàn toàn khỏi bộ nhớ.
REM Tác động: Dùng để chặn AI ném ra những từ vô lý.
REM Ví dụ:
REM - TOP_P=0.9 (Mặc định): Loại bỏ 10% các từ khóa xấu/có khả năng bị điên nhất. Giúp giữ lại 90% bộ từ vựng, không làm AI bị thu hẹp không gian dùng từ mềm mại.
REM - TOP_P=0.1: Chặn đứng 90% từ khóa. Ép AI chỉ được bốc chữ trong một rổ nhỏ các từ đúng logic nhất. Lấy ra output như cái máy.
if not defined TOP_P set "TOP_P=0.9"

REM [TOP_K] (Khoảng giá trị: 1 trở lên)
REM Khái niệm: Màng lọc chốt số lượng chữ chuẩn (Không liên quan tỷ lệ %). TOP_K ép AI chỉ được nhìn đúng tới K cái tên từ khóa điểm cao nhất nằm trên top.
REM Tác động: Gọt đi đuôi chữ xấu. Dùng rất tốt kết hợp với lúc set Temperature thật to. Temperature làm câu từ bay bổng (dễ hỏng), TOP_K sẽ níu lại bảo đảm dù bay bổng kiểu gì thì từ cuối cùng xuất ra cũng được tuyển chọn ngữ pháp.
REM Ví dụ:
REM - TOP_K=40 (Mặc định): Mỗi lần chuẩn bị viết 1 từ, AI chỉ được nhìn 40 cái tên cao điểm nhất để bốc 1 từ lên bảng.
REM - TOP_K=1: Ép AI chỉ được chọn duy nhất tên đỉnh bảng. Hệ quả: chạy chương trình 10 lần thì sẽ phun ra chữ đúng y hệt 10 lần (y xì đúc như photo bài nhau).
if not defined TOP_K set "TOP_K=40"

REM [REPEAT_PENALTY] (Khoảng giá trị: 1.0 trở lên)
REM Khái niệm: Hình phạt lặp từ. Khi AI định dùng lại chữ nó vừa mới xuất ra câu trên, điểm số của từ đó bị đè thụt xuống.
REM Tác động: Phòng chống AI nhảy vào lỗi lặp vô hạn (Ví dụ vòng lập: "Tôi đang đang đang đang").
REM Ví dụ:
REM - REPEAT_PENALTY=1.0: Không trừng phạt (Tắt chế độ này). AI lặp từ thoải mái tùy ý.
REM - REPEAT_PENALTY=1.1 (Mặc định): Mức phạt vừa chuẩn nhất. AI viết tự nhiên, không lặp thành đoạn văn rườm rà.
REM - REPEAT_PENALTY=1.5: Phạt quá nặng. AI sẽ tìm mọi cách chạy trốn từ nó vừa dùng xong. Hậu quả là nó sẽ thốt ra những tự dở hơi không làm được việc.
if not defined REPEAT_PENALTY set "REPEAT_PENALTY=1.1"

REM [SEED] & [REASONING_EFFORT]
REM Khái niệm:
REM - SEED: Khóa định sẵn của chuỗi chọn phần mềm. (-1 là mở hệ phát máy tự tạo/Ngẫu nhiên đổi khác chuỗi).
REM - REASONING_EFFORT: Bắt AI dừng bao lâu trong tiềm thức để nghiền ngẫm kết quả cấu trúc bài. (Chủng hệ như OpenAI đời model o1 mới mở tính năng khóa này).
REM Ví dụ: Chỉnh SEED=42. Khi chạy ứng dụng nhiều lần, bạn sẽ bắt phần mềm này hoạt động cho ra văn bản luôn trùng và có cùng quá trình mắc lỗi. Tiện nhất để xem mình sửa Code đã thực sự vượt cái lỗi cũ ở lượt trước chưa.
if not defined SEED set "SEED=-1"
if not defined REASONING_EFFORT set "REASONING_EFFORT=low"

REM [MAX_TOKENS] (Chỉ số giới hạn vòng trả lời)
REM Khái niệm: Độ dài tối đa bức thư/đoạn tin nhắn cho Mỗi Một lần AI In ra trên cửa sổ trả lời trả về bạn.
REM Tác động: Khống chế việc máy bị treo VRAM của hệ do kéo chuỗi sinh vô hạn.
REM Ví dụ:
REM - MAX_TOKENS=8192: Chỉnh khá cao để phần mềm kịp thời in phun toàn bộ đoạn Code dài vô cấu trả về cửa số mà không phanh gắt, gián đoạn lệnh in cắt ngang trang.
if not defined MAX_TOKENS set "MAX_TOKENS=8192"

REM ---- 5. Dấu thời gian phản hồi máy chủ & Lệnh Mạng ----

REM [HOST] & [PORT]
REM Khái niệm: Điểm kết nối địa chỉ thiết bị máy chủ.
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8080"

REM [BOOT_TIMEOUT], [REQUEST_TIMEOUT], [HEALTH_TIMEOUT], [SHUTDOWN_TIMEOUT]
REM Khái niệm: Tính bằng (Giây). Vòng lặp ngưỡng chờ phần mềm tính giây (gọi khởi chạy máy chủ, trả request gửi API, độ ngậm ping khi gửi nhận truy cập, thoát lưu).
REM Ảnh hưởng: Khi cắm cái não AI (.gguf) nặng quá khổ dung lượng Ram máy lên HDD ổ thường xoay cơ xoắn từ. Tốc bật máy rất trễ. Để BOOT_TIMEOUT=240, nới rông lề giây lên tránh ứng dụng rớt tắt báo văng ứng dụng chả ra đâu.
if not defined BOOT_TIMEOUT set "BOOT_TIMEOUT=120"
if not defined HEALTH_TIMEOUT set "HEALTH_TIMEOUT=2"
if not defined REQUEST_TIMEOUT set "REQUEST_TIMEOUT=300"
if not defined SHUTDOWN_TIMEOUT set "SHUTDOWN_TIMEOUT=5"

REM [COMPAT_RETRY_LIMIT] & [MAX_REQUESTS_PER_MINUTE]
REM Khái niệm: Thông số cố định lần chặn gửi lại phần lỗi API đứt gãy kết nối mạng/ 1 phút tối đa cho thả request.
REM Ảnh hưởng: Nếu AI gặp truy sai ngắt lạp truy gửi không thoát khỏi vô mạch lỗi. Nó chận bay tiền dịch vụ (Thẻ trả API bên ngoài/chặn đập tiền ngu).
if not defined COMPAT_RETRY_LIMIT set "COMPAT_RETRY_LIMIT=8"
if not defined MAX_REQUESTS_PER_MINUTE set "MAX_REQUESTS_PER_MINUTE=60"

REM ---- 6. Thông số ngắt bộ khung phần mềm Agent ----

REM [MAX_ITERATIONS], [MAX_REPEATS], [AGENT_TIMEOUT]
REM Khái niệm: Số vòng cho phép để AI chạy nhiệm vụ trước khi bạn cưỡng chế gạt điện tắt (MAX_ITERATIONS). Số lần ứng dụng cho phép dùng một tool xịt (trượt lặp quá trình) - (MAX_REPEATS), độ rộng thời gian tính chẵn trên giây cả lần quy trình.
REM Ví dụ: MAX_ITERATIONS=25 tức phần mềm chỉ nhồi vòng phân gỡ file tìm cho đủ tối lượng tới chu kỳ thao tác 25 đóng và thoát ngay phần mềm ngắt điện trả cửa sổ do hệ phán quá bí.
if not defined MAX_ITERATIONS set "MAX_ITERATIONS=60"
if not defined MAX_REPEATS set "MAX_REPEATS=3"
if not defined AGENT_TIMEOUT set "AGENT_TIMEOUT=300"

REM ---- 7. Thiết lập bổ sung tập Công cụ ----

REM [WORKSPACE], [EXTRA_ARGS]
REM Khái niệm: Ấn định vùng thiết lập cho phép hộp làm Workspace bảo vệ phần lõi (Code ứng dụng, mã cá nhân).
if not defined WORKSPACE set "WORKSPACE=%~dp0workspace"
if not defined EXTRA_ARGS set "EXTRA_ARGS="

REM [AGENTFORGE_BROWSER_HEADLESS] & [AGENTFORGE_DESKTOP_CONTROL]
REM Khái niệm: Tắt mở xem phần mềm xử quá trình công cụ (Browser).
REM Ví dụ: 0 = Cho khởi duyệt chương trình qua hiển thị tab windows pop-up lên màn. 1 = Chạy dấu nhẹ cửa sổ dưới ngầm task cho bạn không thấy để không chiếm diện tích máy đang mở coi phim (Headless).
if not defined AGENTFORGE_BROWSER_HEADLESS set "AGENTFORGE_BROWSER_HEADLESS=0"
if not defined AGENTFORGE_DESKTOP_CONTROL set "AGENTFORGE_DESKTOP_CONTROL=1"

REM [TOOL_TIMEOUT_*]
REM Khái niệm: Mức hẹn đóng tính chặn Mili-giây (Ms)/ Giây(S). Các Tool khi gửi không truy tải được qua cấu hình.
REM Tác động: AI chạy bộ ứng dụng duyệt tìm, Photoshop. Do web lỗi phản chậm sẽ không để chương trình đóng lag phanh vô cực phần mềm.
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
REM Khái niệm: Lớp phân chốt ứng dụng hạn khóa đọc dòng thiết bị từ Command Line sang (Terminal).
REM Ví dụ: 
REM - SHELL_WORKSPACE_ONLY=1 (Mặc định): An tâm thả AI tạo, truy sửa tệp vì nó KHÔNG bị tràn file thoát khỏi hệ mục phân giới thư Workspace ứng dụng vào máy ổ bộ hệ gốc bạn.
REM - SHELL_WORKSPACE_ONLY=0: Tắt khoá. Dành cho phép uỷ nhiệm, cho dòng AI nhảy thẳng toàn kho máy, hệ máy. (Phải cực am hiểm uỷ phần code chạy riêng nếu không banh ổ cứng bộ nhớ hệ).
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

REM Ensure Playwright browser runtime for browser skill (best effort).
REM If this step fails, core runtime still works, but browser tools may fail.
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo Installing Playwright Chromium runtime...
    python -m playwright install chromium >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Could not auto-install Playwright Chromium runtime.
        echo WARNING: Browser skill may fail until you run:
        echo WARNING:   python -m playwright install chromium
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
if not defined CI (
    if /I not "%AGENTFORGE_NO_PAUSE_ON_FAIL%"=="1" (
        echo.
        echo Startup failed. Press any key to close this window...
        pause >nul
    )
)

:end
popd
exit /b %EXIT_CODE%
