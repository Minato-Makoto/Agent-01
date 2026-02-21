# [■] AGENT-01: HƯỚNG DẪN SỬ DỤNG PHẦN MỀM

Chào mừng bạn đến với Hướng dẫn Sử dụng Agent-01. Tài liệu này cung cấp các hướng dẫn kỹ thuật để cài đặt và thiết lập một Open-source AI Agent. Agent-01 là một phần mềm mã nguồn mở hoạt động trực tiếp trên máy tính cá nhân, trao quyền cho các nhà phát triển và người dùng tự động hóa trình duyệt web, thực thi lệnh terminal, quản lý tập tin cục bộ, và xử lý các yêu cầu phức tạp thành các bước tuần tự cụ thể.

Tập tin khởi chạy chính để ứng dụng hoạt động trên hệ điều hành Windows là: `run.bat`.

---

## [►] PHẦN 1: KHỞI ĐỘNG HỆ THỐNG

Để bắt đầu sử dụng phần mềm, vui lòng thực hiện theo các bước sau:

1. Mở cửa sổ dòng lệnh `cmd` hoặc `PowerShell` tại thư mục gốc chứa mã nguồn của ứng dụng.
2. Khởi chạy bằng lệnh sau:
   ```cmd
   run.bat
   ```
   
**Quy trình Phân tích Khởi động:**
- Ứng dụng sẽ tự động tạo một không gian làm việc an toàn mang tên `workspace`.
- Hệ thống kiểm tra và tự động cài đặt các thư viện Python yêu cầu nếu phát hiện thiếu sót.
- Khởi động máy chủ cục bộ `llama-server` (khi sử dụng tập tin mô hình `.gguf`), hoặc tiến hành kết nối chuẩn xác với dịch vụ API từ xa đã cấu hình.
- Ứng dụng vào trạng thái chờ trực tuyến, sẵn sàng tiếp nhận yêu cầu từ bạn.

---

## [►] PHẦN 2: THIẾT LẬP THÔNG SỐ CẤU HÌNH

Tùy vào nhu cầu sử dụng, bạn có thể thiết lập các tùy chọn tương ứng. Tập tin `run.bat` đóng vai trò là nơi lưu trữ cấu hình chính. Bạn có thể chỉnh sửa trực tiếp bên trong tập tin này bằng công cụ soạn thảo văn bản (như Notepad), hoặc ghi đè thông số trực tiếp từ dòng lệnh:

`set MAX_TOKENS=8192 && run.bat`

### 2.1 Môi trường Xử lý (`PROVIDER`)
Phân bổ luồng xử lý mô hình ngôn ngữ dựa trên thiết bị máy tính cá nhân hoặc dịch vụ đám mây.

*   **CHẾ ĐỘ CỤC BỘ (Mặc định):**
    *   **Thiết lập:** `set PROVIDER=local`
    *   **Đặc điểm:** Tối ưu hóa tính toàn vẹn dữ liệu bằng cách sử dụng sức mạnh phần cứng máy tính nội bộ của bạn. Yêu cầu tải sẵn mô hình `.gguf` và khai báo đường dẫn tại biến `MODEL_PATH`.
    *   **Tối ưu hiệu suất:** Cài đặt `GPU_LAYERS=-1` để chuyển toàn bộ cấu trúc mạng nơ-ron sang bộ nhớ đồ họa (VRAM) nhằm gia tăng tốc độ xử lý phản hồi.

*   **CHẾ ĐỘ TỪ XA:**
    *   **Thiết lập:** `set PROVIDER=openai_compatible`
    *   **Đặc điểm:** Kết nối tới các API dịch vụ bên ngoài (như OpenAI, Anthropic, v.v.). Đòi hỏi cung cấp `BASE_URL`, `MODEL_ID`, và thiết lập biến môi trường chứa bộ khóa API (`API_KEY_ENV`).
    *   **Tối ưu hiệu suất:** Phù hợp với nhu cầu xử lý quy trình logic phức tạp mà thiết bị phần cứng của bạn không đáp ứng được.

### 2.2 Tùy chỉnh Các Chỉ số Suy luận
Sửa đổi các thông số nhận thức để nâng cao chất lượng phản hồi từ phần mềm.

*   `CTX_SIZE`: Kích thước vùng nhớ ngữ cảnh (số lượng token) cho phiên làm việc. Khuyến nghị tăng thông số (ví dụ: `16384`) khi bạn cần cung cấp một tệp tài liệu lớn, hoặc một thư mục mã nguồn đồ sộ để phân tích nguyên văn.
*   `TEMPERATURE`: Điều chỉnh tính đa dạng của chuỗi đầu ra.
    *   `0.1`: Cho ra kết quả độ chính xác cao nhất và luôn bám sát dữ liệu cấu trúc gốc. Tối ưu cho thao tác sinh và gỡ lỗi mã nguồn lập trình.
    *   `0.7`: Mở rộng khả năng chọn từ vựng ngẫu nhiên. Phù hợp cho thảo luận phương án thiết kế phần mềm.
*   `MAX_TOKENS`: Mức trần cho quá trình phát sinh token đầu ra. Chỉ số `8192` giúp hạn chế hiện tượng kết quả tạo mã nguồn hoặc văn bản dài bị dừng đột ngột giữa chừng.

---

## [►] PHẦN 3: TÙY CHỌN BẢO MẬT & MÔI TRƯỜNG AN TOÀN

Open-source AI Agent có khả năng tự động thực thi các dòng lệnh trong hệ điều hành của bạn, do đó, các cài đặt bảo mật thư mục sau đây được bật mặc định.

*   **Môi trường Hộp cát (Sandbox) (`SHELL_WORKSPACE_ONLY`):**
    *   Giá trị đang được đặt là `1`. Trợ lý AI bị giới hạn hoạt động nghiêm ngặt trong thư mục cấu hình: các thay đổi tập tin và tương tác lệnh shell bị hạn chế cấp phép chỉ trên phạm vi thư mục `./workspace`.
    *   **Lưu ý:** Chỉnh thông số này thành `0` sẽ vô hiệu hóa hoàn toàn cơ chế bảo mật (Sandbox), trao đặc quyền truy cập trên toàn thiết bị cho ứng dụng. Chỉ khi thực sự tự quản trị được mức độ bảo mật thì mới sử dụng thiết lập số 0.
*   **Ngắt tự động kết nối (`MAX_ITERATIONS` & `MAX_REPEATS`):**
    *   Phòng ngừa hiện tượng xử lý phần mềm treo vô hạn. `MAX_ITERATIONS=25` ấn định vòng lặp xử lý sẽ bị dừng ứng dụng ngay lập tức nếu tác vụ vẫn chưa hoàn thành xong sau 25 bước tương tác chu kỳ nội bộ.

---

## [►] PHẦN 4: HƯỚNG DẪN VIẾT CÂU LỆNH YÊU CẦU

Giao tiếp với mô hình Agent đòi hỏi cấu trúc viết Prompt chuyên biệt hơn so với trợ lý nội dung (Chatbot AI). Các lệnh đưa vào nên có định nghĩa rõ ràng mục tiêu tổng, đi kèm định dạng theo bước mô tả thay vì hỏi ngắn gọn.

### [!] Cách viết chưa tối ưu (Chỉ hợp Chatbot)
> "Viết một đoạn mã Python để tải thông tin giá tiền số."

### [★] Cách viết chuẩn (Dành cho Agent)
> "Mục tiêu: Viết ứng dụng theo dõi giá Crypto.
> 1. Sử dụng tính năng trình duyệt web của bạn để truy cập `coinmarketcap.com`.
> 2. Phân tích cấu trúc thư mục DOM nhằm tìm kiếm thành phần giao diện chứa mức Bitcoin giá mới nhất.
> 3. Tạo một tập lệnh Python theo nguyên lý thu thập dữ liệu (web scraper) trực tiếp và xuất thành tệp tên `crypto.py` trong workspace.
> 4. Hãy sử dụng tính năng bash shell command để khởi chạy tập lệnh này và hiển thị thông báo thành công cho tôi kiểm tra."

**Lý do đạt chuẩn:** Câu lệnh này đưa rõ yêu cầu triển khai theo lộ trình. Ứng dụng Open-source AI Agent khi tiếp nhận sẽ tự vận hành liên hoàn các bộ công cụ tính năng (Web Browser - Command Line - Text Editor) theo tuần tự để cung cấp đúng quy trình dữ liệu bạn đề ra.

Hệ thống đang chờ lệnh phản hồi từ cửa sổ Terminal.
