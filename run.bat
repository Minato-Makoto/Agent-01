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
REM 2) Chế độ Từ xa (Sử dụng API bên ngoài):
REM    set PROVIDER=openai_compatible
REM    set BASE_URL=https://api.openai.com/v1
REM    set MODEL_ID=gpt-4o
REM    set OPENAI_API_KEY=YOUR_KEY
REM    run.bat
REM
REM 3) Chế độ An toàn (Khóa quyền sửa đổi tập tin hệ thống):
REM    set SHELL_WORKSPACE_ONLY=1
REM    run.bat
REM
REM [i] HƯỚNG DẪN CẤU HÌNH THÔNG SỐ
REM ------------------------------------------------------------
REM Người dùng có thể thay đổi vĩnh viễn các thông số bằng cách chỉnh sửa giá trị sau dấu "=" ở dưới.
REM Hoặc thiết lập tạm thời thông qua Command Prompt trước khi chạy:
REM   set MAX_TOKENS=4096 && run.bat
REM ============================================================

REM ---- 1. Hệ thống & Chế độ Vận hành (Provider Mode) ----

REM [PROVIDER]
REM Khái niệm: Xác định nền tảng phần cứng sẽ thực hiện suy luận AI.
REM Tác động: Quyết định việc phần mềm sử dụng tài nguyên máy tính cá nhân (local) hay thông qua dịch vụ đám mây (openai_compatible).
REM Ví dụ:
REM - PROVIDER=local (Mặc định): Đảm bảo quyền riêng tư tuyệt đối, hoạt động ngoại tuyến, sử dụng card đồ họa (GPU) hoặc vi xử lý (CPU) trên máy.
REM - PROVIDER=openai_compatible: Kết nối tới các dịch vụ API hiệu suất cao bên ngoài (như OpenAI, xử lý các mô hình ngôn ngữ lớn).
if not defined PROVIDER set "PROVIDER=local"

REM ---- 2. Cấu hình Máy chủ Cục bộ (Áp dụng khi PROVIDER=local) ----

REM [SERVER_EXE] & [MODEL_PATH]
REM Khái niệm: Đường dẫn đến tập tin thực thi nền tảng AI (SERVER_EXE) và tập tin dữ liệu mô hình ngôn ngữ (MODEL_PATH - định dạng .gguf).
REM Tác động: Bắt buộc phải có để khởi động chế độ cục bộ. Việc cung cấp sai đường dẫn sẽ khiến phần mềm không thể khởi tạo và báo lỗi.
REM Ví dụ:
REM - MODEL_PATH="D:\Models\AI_Llama.gguf"
if not defined SERVER_EXE set "SERVER_EXE=%~dp0llama-b8069-bin-win-cuda-13.1-x64\llama-server.exe"
if not defined MODEL_PATH set "MODEL_PATH=D:\Personal\MinatoZeroFace\AI Agent\model\Llama-3.3-8B-Instruct.Q4_K_M.gguf"

REM ---- 3. Cấu hình Máy chủ Từ xa (Áp dụng khi PROVIDER=openai_compatible) ----

REM [BASE_URL], [MODEL_ID], [API_KEY_ENV]
REM Khái niệm: Thiết lập thông tin mạng kết nối tới máy chủ cung cấp API. Yêu cầu nhập đúng tên miền, mã mô hình, và tên biến môi trường chứa khóa bảo mật (API Key).
REM Tác động: Nếu thiếu thông tin quản lý API hoặc khóa bảo mật không chính xác, máy chủ bên ngoài sẽ từ chối quyền truy cập.
if not defined BASE_URL set "BASE_URL=http://127.0.0.1:8080"
if not defined MODEL_ID set "MODEL_ID=local"
if not defined API_KEY_ENV set "API_KEY_ENV=OPENAI_API_KEY"

REM ---- 4. Tùy chỉnh Suy luận (Inference Tuning) ----

REM [CTX_SIZE] (Kích thước: 1024, 2048, 4096, 8192, 16384...)
REM Khái niệm: Kích thước vùng nhớ ngữ cảnh. Đại diện cho số lượng từ ngữ (token) tối đa mà AI có thể lưu trữ và ghi nhớ trong một phiên làm việc.
REM Tác động: Tham số càng lớn, phần mềm càng có khả năng đọc hiểu các tài liệu dài hoặc mã nguồn lớn. Tuy nhiên, nó sẽ tiêu thụ đáng kể dung lượng bộ nhớ RAM/VRAM. Yêu cầu cấu hình máy tính phù hợp.
REM Ví dụ:
REM - CTX_SIZE=8192: Phù hợp với các thiết bị máy tính cá nhân phổ thông, đáp ứng đủ độ dài ngữ cảnh tiêu chuẩn.
REM - CTX_SIZE=16384: Dành cho việc xử lý hàng loạt tài liệu phức tạp, yêu cầu dung lượng RAM và VRAM (Card đồ họa) lớn để tránh lỗi quá tải bộ nhớ.
if not defined CTX_SIZE set "CTX_SIZE=16384"

REM [GPU_LAYERS] & [THREADS]
REM Khái niệm: Thông số phân bổ khối lượng tính toán cấu trúc AI giữa Card đồ họa (GPU) và Bộ vi xử lý trung tâm (CPU).
REM Tác động: Thay đổi thông số này trực tiếp quyết định tốc độ phản hồi văn bản của phần mềm.
REM Ví dụ: 
REM - GPU_LAYERS=-1 (Mặc định): Chuyển toàn bộ các lớp đồ thị mạng nơ-ron lên card đồ họa nhằm đạt tốc độ xử lý tối đa. Nếu thiết bị xuất hiện lỗi tràn VRAM, người dùng có thể hạ dần giá trị xuống (ví dụ 30 hoặc 20).
REM - THREADS=0 (Mặc định): Cho phép phần mềm tự động tối ưu hóa số luồng sử dụng trên CPU dựa trên cấu hình phần cứng nhàn rỗi.
if not defined GPU_LAYERS set "GPU_LAYERS=-1"
if not defined THREADS set "THREADS=0"

REM [TEMPERATURE] (Khoảng giá trị: 0.0 đến 2.0)
REM Khái niệm: Mức độ ngẫu nhiên trong việc lựa chọn từ vựng của AI để sinh văn bản.
REM Tác động: Hệ số thấp khiến cấu trúc văn bản được duy trì ổn định, nhất quán và độ chính xác kỹ thuật cao. Hệ số cao giúp phần mềm diễn đạt đa dạng và linh hoạt hơn.
REM Ví dụ:
REM - TEMPERATURE=0.1 (Mặc định): Lý tưởng cho lập trình, gỡ lỗi mã nguồn (coding) và trích xuất dữ liệu. Thông tin trả về bám sát cấu trúc logic thuần túy.
REM - TEMPERATURE=0.8: Thích hợp cho công việc sáng tạo nội dung, soạn thảo văn bản, yêu cầu sự đa dạng trong cách diễn đạt ngôn ngữ tự nhiên.
if not defined TEMPERATURE set "TEMPERATURE=0.1"

REM [TOP_P] (Khoảng giá trị: 0.0 đến 1.0)
REM Khái niệm: Lấy mẫu theo xác suất cộng dồn (Nucleus Sampling). AI sẽ chọn các từ có khả năng xuất hiện cao nhất cho đến khi tổng xác suất cộng dồn bằng P, rồi loại phần còn lại.
REM Tác động: Giúp thu hẹp danh sách các từ vựng hợp lý, giảm khả năng phần mềm sinh ra các từ ngữ thiếu liên kết hoặc không phù hợp ngữ cảnh.
REM Ví dụ:
REM - TOP_P=0.9 (Mặc định): Loại bỏ 10% các từ vựng ngoại lai có xác suất thấp nhất. Đảm bảo cấu trúc văn bản ổn định trong khi vẫn giữ lại phần lớn khả năng sáng tạo ngôn từ.
REM - TOP_P=0.1: Loại bỏ 90% từ vựng. Cưỡng chế AI chỉ chọn tập nhỏ các từ khóa chuẩn xác định, khiến đầu ra mang đậm tính khuôn mẫu cơ khí.
if not defined TOP_P set "TOP_P=0.9"

REM [TOP_K] (Khoảng giá trị: 1 trở lên)
REM Khái niệm: Cắt giảm theo số lượng thuần túy. Ép buộc AI chỉ được chọn từ tiếp theo trong danh sách K từ có xác suất cao điểm nhất.
REM Tác động: Kết hợp hiệu quả cùng thông số Temperature để ngăn việc văn bản bị lạc đề, bảo đảm các chữ sinh ra sau cùng đều nằm trên cùng hệ ngữ pháp chuẩn xác.
REM Ví dụ:
REM - TOP_K=40 (Mặc định): Trong mỗi bước xử lý sinh từ, phần mềm chỉ chọn từ nằm trong số 40 lựa chọn có tỷ lệ chính xác phù hợp cao nhất.
REM - TOP_K=1: Ép cấu hình AI chỉ được chọn duy nhất từ đứng đầu. Khi đó phần mềm hoạt động như máy xử lý tĩnh, 10 lượt sinh câu trả lời thì kết quả xuất ra giống hệt nhau 10 lần.
if not defined TOP_K set "TOP_K=40"

REM [REPEAT_PENALTY] (Khoảng giá trị: 1.0 trở lên)
REM Khái niệm: Mức điểm phạt được áp dụng nhằm điều chỉnh việc trí tuệ nhân tạo lạm dụng lặp lại một cụm từ mà nó đã xuất ra trước đó.
REM Tác động: Phương pháp ngăn chặn AI rơi vào lỗi chạy vòng lặp đoạn văn bản vô thời hạn.
REM Ví dụ:
REM - REPEAT_PENALTY=1.0: Vô hiệu hóa tính năng phạt. Phần mềm có thể lặp từ liên tục theo cấu trúc dữ liệu thô.
REM - REPEAT_PENALTY=1.1 (Mặc định): Hệ số bù trừ tối ưu nhất cho văn phong tự nhiên, chống hiện tượng lặp từ và giúp văn bản rõ ràng.
REM - REPEAT_PENALTY=1.5: Mức phạt thiết lập nặng. Khiến AI lập tức né tránh hoàn toàn từ vừa sử dụng, thường dẫn đến việc cấu trúc ngữ pháp bị gượng ép thiếu tự nhiên.
if not defined REPEAT_PENALTY set "REPEAT_PENALTY=1.1"

REM [SEED] & [REASONING_EFFORT]
REM Khái niệm:
REM - SEED: Khóa định sẵn của chuỗi tự sinh giả ngẫu nhiên trong hệ thống. Tham số -1 cho phép thuật toán lấy một giá trị thời gian ngẫu nhiên cơ bản hệ thống.
REM - REASONING_EFFORT: Mức nỗ lực suy luận ưu tiên, ấn định thời gian AI nghiên cứu và phân rã lập luận logic trước khi lập cấu trúc kết quả (Chuyên biệt cho dòng mô hình tư duy nâng cao như OpenAI o1).
REM Ví dụ: Khi cấu hình bằng giá trị SEED=42, đối với cùng một dữ liệu đầu vào, phần mềm sẽ tái lập chính xác một kết quả đầu ra giống nhau 100%. Rất có ích cho việc khoanh vùng và kiểm tra rà soát phần mền gỡ lỗi (Debugging).
if not defined SEED set "SEED=-1"
if not defined REASONING_EFFORT set "REASONING_EFFORT=low"

REM [MAX_TOKENS]
REM Khái niệm: Khối lượng số token tối đa giới hạn biên độ cho một lượt văn bản phản hồi đầy đủ của hệ thống.
REM Tác động: Hạn chế rủi ro phần mềm phải sinh chuỗi văn bản quá tải, vượt biên gây lãng phí tài nguyên VRAM.
REM Ví dụ:
REM - MAX_TOKENS=8192: Chỉ số an toàn cho phép phần mềm lập trình đáp ứng xuất khối lượng mã nguồn đủ dài ra màn hình Terminal mà không mắc lỗi tự động gián đoạn giữa chừng do chạm ngưỡng trần phần mềm.
if not defined MAX_TOKENS set "MAX_TOKENS=8192"

REM ---- 5. Dấu thời gian phản hồi máy chủ & Lệnh Mạng ----

REM [HOST] & [PORT]
REM Khái niệm: Cấu hình giao thức cổng mạng kết nối thiết bị địa chỉ IP hiện tại.
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8080"

REM [BOOT_TIMEOUT], [REQUEST_TIMEOUT], [HEALTH_TIMEOUT], [SHUTDOWN_TIMEOUT]
REM Khái niệm: Thời hạn thời gian tối đa tối đa (đơn vị: giây) ấn định cho tác vụ phần mềm đợi phản hồi từ tiến trình lõi. Bao gồm thời gian khởi động máy chủ hệ điều hành, thời gian tiếp nhận truyền xuất qua cổng API, thời lượng kiểm định hoạt động ứng dụng đang phân giải và khung giới hạn thoát chu kỳ khép chương trình.
REM Tác động: Trên máy chủ chạy định dạng dữ liệu có kích thước khủng dùng ổ cơ khí lưu trữ (HDD) chậm trễ nhịp đọc, có nguy cơ ứng dụng bị báo văng ngắt lỗi do quá hạn kết nối thời gian. Giải pháp là tinh chỉnh tham số độ nới giãn cấu hình BOOT_TIMEOUT tăng mốc biên cao (ví dụ: 240 hoặc trên hệ số đó).
if not defined BOOT_TIMEOUT set "BOOT_TIMEOUT=120"
if not defined HEALTH_TIMEOUT set "HEALTH_TIMEOUT=2"
if not defined REQUEST_TIMEOUT set "REQUEST_TIMEOUT=300"
if not defined SHUTDOWN_TIMEOUT set "SHUTDOWN_TIMEOUT=5"

REM [COMPAT_RETRY_LIMIT] & [MAX_REQUESTS_PER_MINUTE]
REM Khái niệm: Bức tường hệ giới hạn định lượng tần suất tự động cố thử kết nối trở lại API (khi đứt gãy kết nối hoặc bị ngắt tải) cùng giới biên định mức số lần cung cấp phản hồi request trong tần số thời gian vòng đếm một phút tính bằng cơ chế.
REM Tác động: Xây dựng cơ chế an toàn cấp độ giới hạn (Rate limit protection). Nhằm triệt tiêu nguyên cớ phần mềm hoạt động gọi truy vấn kết nối mất thông tin không ngừng gây nên hiện tượng thiệt hại thanh toán tiêu thụ tín dụng tài khoản thương mại đám mây ở bên dịch vụ từ xa.
if not defined COMPAT_RETRY_LIMIT set "COMPAT_RETRY_LIMIT=8"
if not defined MAX_REQUESTS_PER_MINUTE set "MAX_REQUESTS_PER_MINUTE=60"

REM ---- 6. Thông số ngắt bộ khung phần mềm Agent ----

REM [MAX_ITERATIONS], [MAX_REPEATS], [AGENT_TIMEOUT]
REM Khái niệm: Tham số cấu hình mốc giới hạn kiểm soát đặc vụ máy móc trí tuệ nhân tạo (Agent) thực hiện tác vụ tự trị (Autonomous). Các thông số giới hạn chặn rủi ro vòng lặp bao gồm số lượng thao tác chu kỳ (MAX_ITERATIONS), số lượng rào kiểm gọi công cụ hành động liên tiếp thừa (MAX_REPEATS), và độ mở rộng giới hạn theo tính quy chuẩn thời gian trên toàn phiên tiến trình vòng lập công việc (AGENT_TIMEOUT).
REM Ví dụ: MAX_ITERATIONS=25 tương đương giới hạn đặc vụ Agent phân rã, xử lý thử nghiệm lỗi và điều hướng công cụ xử cục bộ ở hạn mức tối đa 25 lần hoạt động thao tác hệ điều hành chuyên biệt. Quá số lần cho phép máy móc đứt xử lý tiến trình ngắt giao thức.
if not defined MAX_ITERATIONS set "MAX_ITERATIONS=25"
if not defined MAX_REPEATS set "MAX_REPEATS=3"
if not defined AGENT_TIMEOUT set "AGENT_TIMEOUT=300"

REM ---- 7. Thiết lập bổ sung tập Công cụ ----

REM [WORKSPACE], [EXTRA_ARGS]
REM Khái niệm: Thiết lập cấu trúc gốc thư mục nhằm mục đích cấp quyền mở không gian cho đặc vụ Agent xử lý dữ liệu và môi trường cho không gian biến dòng lệnh (Command Line Interface - CLI).
if not defined WORKSPACE set "WORKSPACE=%~dp0workspace"
if not defined EXTRA_ARGS set "EXTRA_ARGS="

REM [AGENTFORGE_BROWSER_HEADLESS] & [AGENTFORGE_DESKTOP_CONTROL]
REM Khái niệm: Các tùy chọn kiểm soát môi trường giao diện cho phần mềm điều hướng tự động thao tác trên trình duyệt mở web.
REM Ví dụ: Cấu hình cài đặt giá trị bằng 0 sẽ khởi chạy phần mềm trực tiếp tự thao tác nổi (Visible browser window). Tại giá trị 1 trợ lý trí tuệ nhân tạo sẽ âm thầm chạy tiến trình nền ảo ẩn ở hệ điều hành trên máy (Headless process background) để bảo đảm môi trường kiểm soát màn hình hiện thời của thiết bị không hiện tab nhảy chặn tập trung.
if not defined AGENTFORGE_BROWSER_HEADLESS set "AGENTFORGE_BROWSER_HEADLESS=0"
if not defined AGENTFORGE_DESKTOP_CONTROL set "AGENTFORGE_DESKTOP_CONTROL=1"

REM [TOOL_TIMEOUT_*]
REM Khái niệm: Tham số mốc chốt chặn (tính dựa theo hệ giây và mili-giây) lập giới thiết bị cho phân rã ứng dụng quy chuẩn mạng cục diện hay bên công cụ hệ trợ lý hình đồ họa.
REM Tác động: Xử lý và triệt hạ nguy cơ thiết bị đơ hệ ứng dụng chủ (lag) xuất phát vì lỗi mạng hoặc hệ thống trình cắm (plugin).
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
REM Khái niệm: Hệ thống khoanh vùng môi trường an toàn nhằm hạn chế rủi ro cho truy vấn giao thức lệnh thực thi tại cửa sổ dòng lệnh mã nguồn máy (Command terminal).
REM Ví dụ: 
REM - SHELL_WORKSPACE_ONLY=1 (Mặc định): Bật môi trường hộp cát cách ly, giúp người dùng an tâm đảm bảo ứng dụng đặc vụ AI khi tương tác hệ điều hành hoàn toàn không xâm nhập quyền tác động can thiệp ghi xóa thông số vượt phép vào những thư mục ứng dụng trên máy nằm hệ ngoài và loại trừ khu vực Workspace. 
REM - SHELL_WORKSPACE_ONLY=0: Vô hiệu hóa vùng không gian hộp cát. Mở rộng ranh giới truy xuất tài liệu dành cho quá trình nhà phát triển thao tác cho toàn khối (Khuyến cáo thiết lập khi quy chuẩn chuyên môn thực thi nằm trên máy ảo hay môi trường không chứa tài liệu mã chính).
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
