# Kế hoạch nâng cấp Agent-01 v1.1.1

Mục tiêu: Cập nhật Agent-01 thành một assistant mạnh mẽ cho người mới, tập trung vào khả năng điều khiển PC, sử dụng phần mềm local và tự động hóa toàn bộ quá trình tạo project (scaffolding).

## Đề xuất Thay đổi

### 1. Nâng cấp và Chuẩn hóa Hệ thống Skills
*   **Xóa các skill cũ:** Dọn dẹp thư mục `workspace/skills/` hiện tại (các skill cũ như `browser`, `file_operations` với file name không đồng nhất).
*   **Port skills mới từ `skills ref`:** Lọc các package phù hợp với định hướng điều khiển Local PC của user.
    *   `app-builder`: Dựng project hoàn chỉnh (codebase scaffolding).
    *   `computer-use-agents`: Điều khiển chuột, phím, UI cục bộ.
    *   `powershell-windows`: Giao tiếp native với hệ điều hành Windows qua terminal.
    *   `file-organizer`: Thao tác thao tác file, thư mục chuẩn xác.
    *   `browser-automation`: Trình mô phỏng trình duyệt để test web nội bộ.
    *   `web_search` (Tavily/Exa): Khôi phục mảng search web với format chuẩn.
*   **Chuẩn hóa tên file:** Toàn bộ file cấu hình chính của mỗi skill dùng chuẩn duy nhất `SKILL.md`. Các file phụ trợ đính kèm trong thư mục skill đó sẽ được giữ nguyên (ví dụ: thư mục `templates/` của `app-builder`).

### 2. Tối ưu ToolLoop Config (`max_iterations`)
*   **Sửa đổi `run.bat`:**
    *   Cập nhật `set MAX_ITERATIONS=25` (thay vì 10). Mức 25 phù hợp hơn với các task kết hợp research + code + test.
*   **Sửa đổi mã nguồn Python (`src/agentforge/`):**
    *   `cli_runtime.py`, `agent_core.py`, `tool_loop.py`: Loại bỏ các hardcode fallback `10`. Bắt buộc tham số `max_iterations` phải được inject từ lệnh CLI (từ `run.bat` / args argument list), đảm bảo `run.bat` (hoặc sys.argv) là Single Source of Truth duy nhất cho tham số này. Nếu không truyền, system sẽ báo lỗi thay vì fallback về 10, TRỪ phi đang chạy pytest (ở đó test fixture phải truyền thông số này).

### 3. Cập nhật Documentation & Versioning
*   **`workspace/IDENTITY.md`:** Bump version lên `1.1.1`. Cập nhật Role để phản ánh khả năng "Project Scaffolding & Native PC Control".
*   **`README.md`:** Cập nhật các thông tin tương ứng chuẩn 1.1.1.
*   **`CHANGELOG.md`:** Thêm block release note cho v1.1.1.

## Kế hoạch Kiểm thử (Verification Plan)
### Kiểm thử Tự động (Automated Tests)
*   **Chạy Pytest:** Chạy `python -m pytest tests/` để đảm bảo hệ thống core, ToolLoop và argparse không bị lỗi sau khi xóa fallback `10`.
### Kiểm thử Thủ công (Manual Verification)
*   **Khởi động bằng run.bat:** Chạy `run.bat` để đảm bảo hệ thống nạp đủ số lượng skills mới và file `skill.md` có parse thành công không (gõ lệnh `skills` trong terminal Agent).
*   **Test vòng lặp tool:** Chạy 1 lệnh powershell nội bộ `echo "test"` để thấy system không bị đứt tại ToolLoop.
