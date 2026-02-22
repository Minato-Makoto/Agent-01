# [■] Agent-01: Hướng Dẫn Sử Dụng Offline Agent

Chào mừng bạn đến với Hướng dẫn Sử dụng Agent-01! Tài liệu này sẽ giúp bạn cài đặt, thiết lập và sử dụng Offline AI Agent của riêng mình.

Agent-01 là một dự án được thiết kế để chạy **100% offline** ngay trên máy tính Windows, trao quyền sử dụng PC cho LLM, ví dụ như: sử dụng trình duyệt web, Adobe Suite, thực thi lệnh hệ thống, quản lý file và xử lý các yêu cầu của bạn thông qua giao tiếp bằng ngôn ngữ tự nhiên,v.v.v... mà không cần kết nối internet!
Ứng dụng hoạt động trên hệ điều hành Windows bằng cách chạy file `run.bat`.

---

## [+] Phần 1: Khởi Động Hệ Thống

Download **llama-server.exe** tại: https://github.com/ggml-org/llama.cpp/releases và giải nén vào thư mục `llama-server` của dự án.
Cài đặt các thông số cần thiết trong file `run.bat` bằng Notepad hoặc các phần mềm tương tự, save lại và double click file `run.bat` để khởi động.
Hệ thống sẽ tự động kiểm tra và cài đặt các thư viện cần thiết nếu máy bạn chưa có (Đoạn duy nhất cần internet).

---

## [*] Phần 2: Thiết Lập Cấu Hình

Bạn có thể dễ dàng tùy chỉnh Agent-01 để phù hợp với nhu cầu sử dụng. Tập tin `run.bat` là nơi lưu trữ các cấu hình chính. Bạn có thể mở và sửa file này bằng các trình soạn thảo mã (như Notepad), hoặc ghi đè tạm thời các thông số ngay khi gõ lệnh trên terminal, ví dụ:

`set MAX_TOKENS=8192 && run.bat`

Trong file `run.bat` có các chú thích và ví dụ cho từng thông số để bạn có thể tùy chỉnh phù hợp với cấu hình máy tính của mình.

### 2.1 Offline & Online Mode (`PROVIDER`)

*   **Offline mode (Mặc định & Khuyên dùng):**
    *   **Cách thiết lập:** `set PROVIDER=local` cùng với `MODEL_PATH=` là đường dẫn đến model GGUF trên máy tính của bạn.
    *   **Mô tả:** Chế độ này chạy 100% offline bằng phần cứng thiết bị, sử dụng các model AI GGUF open-source.

*   **Online mode (Sử dụng API từ xa):**
    *   **Cách thiết lập:** `set PROVIDER=openai_compatible`
    *   **Mô tả:** Sử dụng để gọi LLM thông qua API của các nhà cung cấp như OpenAI, Anthropic, Google, ...
    *   **Cách setup API ENV:**
        1. Bấm nút Start trên bàn phím, gõ chữ: env
        2. Chọn "Edit the system environment variables" (Sửa đổi biến môi trường hệ thống).
        3. System Properties hiện ra, bạn bấm nút "Environment Variables..." ở dưới cùng.
        4. Ở phần User variables, bạn bấm nút New...
        5. Điền vào đó:
            Variable name: OPENAI_API_KEY
            Variable value: sk-12344566778... (Dán thật chính xác API Key của bạn vào đây).
        6. Bấm OK.

### 2.2 Tùy Chỉnh Bộ Não Của AI
Sửa đổi cách AI Agent suy nghĩ và phát sinh văn bản để có chất lượng đầu ra tốt hơn.

*   **`CTX_SIZE` (Khả năng ghi nhớ):** Bộ nhớ ngắn hạn của AI (tính bằng token). Cần thông số cao (VD: `16384`) để AI có thể đọc các tài liệu dài và xử lý các yêu cầu phức tạp.
*   **`TEMPERATURE` (Sự sáng tạo):** Điều chỉnh sự sáng tạo của AI Agent trong câu trả lời (Thấp = logic/ ít sáng tạo, Cao = sáng tạo/ nhiều ý tưởng).
    *   `0.1`: Logic, phân tích và độ chính xác cực cao. Tối ưu khi sinh mã nguồn, khai báo biến hoặc lập dàn bài kỹ thuật.
    *   `0.7`: Sáng tạo và mang văn phong giao tiếp tự nhiên. Phù hợp nhất cho thảo luận và phát triển ý tưởng.
*   **`MAX_TOKENS` (Độ dài đầu ra):** Độ dài tối đa tính theo từng chữ cho mỗi lần phản hồi của model. Chỉ số như `8192` vẫn có khả năng gặp hiện tượng mất chữ hoặc ngừng phản hồi với các kết quả dài.

---

## [!] Phần 3: Tính Năng Bảo Mật & Môi Trường An Toàn

Vì Offline Agent có tính năng chạy command trên máy tính nên đi kèm với nó là các cơ chế bảo vệ nghiêm ngặt để đảm bảo AI không vô tình phá hủy hệ thống.

*   **Default sandbox (`SHELL_WORKSPACE_ONLY`):**
    *   Giá trị luôn được cài sẵn là `1`. Trợ lý của bạn bị khóa trong một không gian hoạt động an toàn. Mọi lệnh sửa file hay kịch bản shell chỉ được ép chạy bên trong thư mục `./workspace`.
    *   **[!] Cảnh Báo:** Đổi giá trị này thành `0` tức là vô hiệu hóa sandbox, cho phép AI truy cập sửa tên tệp trên toàn máy tính.
*   **Anti-loop (`MAX_ITERATIONS` & `MAX_REPEATS`):**
    *   Để tránh các trường hợp model tạo loop tool và lặp vô tận, `MAX_ITERATIONS=60` giữ cho hệ thống sẽ tự kết thúc nếu model gọi 60 lần tool liên tục. (Tăng lên nếu bạn cần tạo nhiều file và ước tính được lượt sử dụng tool của model)

---

## [>] Phần 4: Giao tiếp với AI Agent

Phần trả lời của AI Agent vẫn phụ thuộc vào model bạn chọn sử dụng, hệ thống chỉ cung cấp các công cụ và môi trường để LLM tiến hóa lên AI Agent.
Hoạt động tốt với các mô hình 4B-8B dành cho máy tính tầm trung (Intel i7, 32GB Ram, RTX 3070ti).

---

## [>] Phần 5: LLM Download
Các bạn có thể tìm và download các model GGUF tại: https://huggingface.co/

---

## [>] Phần 6: Cá nhân hóa Agent (users & developers)
*   **User:** 
    *   File `SOUL.md` và `USER.md` là nơi để bạn cá nhân hóa Agent. 
    *   `SOUL.md`: Nơi để bạn cài đặt tính cách, vai trò, và các quy tắc ứng xử, hành vi của Agent.
    *   `USER.md`: Nơi để bạn điền các thông tin cá nhân của bản thân, giúp Agent hiểu và phục vụ bạn tốt hơn.
*   **Developer:** 
    *   Với các developer, mọi người đều có thể fork dự án và phát triển thêm hoặc viết lại toàn bộ mã nguồn bằng AI CLI trên IDE như VSCode, Antigravity, v.v...
    *   Bộ skill cũng thế, download hoặc tự viết ra 1 file `SKILL.md` và nói với AI CLI đăng ký skill cho Agent-01. Đây là cách dự án tránh việc Agent bị dính prompt injection không mong muốn.

---

## [Ω] Lời ngỏ từ sản xuất:
Đây là dự án được tạo ra hoàn toàn 100% bằng AI Generator nên chắc chắn không thể tránh khỏi các sai sót, dự án vẫn sẽ được tiếp tục hoàn thiện dần theo quỹ thời gian mà mình có, HOẶC CHÍNH CÁC BẠN LÀ NGƯỜI SẼ HOÀN THÀNH NÓ. Đừng ngần ngại mà dùng project này như 1 món đồ có thể tháo lắp được, vì code được viết bởi AI nên AI có thể hoàn toàn đọc hiểu code, hãy hỏi nó để biết được thứ mà chính người tạo ra nó cũng không biết. Chúc các bạn thành công và chơi game AI 2026 này vui vẻ!
Thanks & Best Regards,
Minato.
https://minato-makoto.github.io 