# BLUEPRINT — Agent-01 (AgentForge Runtime)

> Version: **1.1.1** · Python 3.10+ · Windows-first · Single launcher: `run.bat`

---

## 1) Tổng quan dự án

Agent-01 là một **Offline AI Agent** được thiết kế để chạy **100% offline** ngay trên máy tính Windows, trao quyền sử dụng PC cho LLM. Điểm thiết kế cốt lõi:

- **100% Offline / Privacy-First**: Ứng dụng chạy trực tiếp bằng phần cứng thiết bị thông qua local `llama-server` và các model GGUF mã nguồn mở. Không yêu cầu internet.
- **Empowering PC for LLM**: Agent có khả năng sử dụng trình duyệt web, Adobe Suite, thực thi lệnh hệ thống, và quản lý tập tin cục bộ thông qua giao tiếp bằng ngôn ngữ tự nhiên.
- **Single Launcher**: Khởi chạy dễ dàng và cấu hình thông số linh hoạt trên duy nhất một file `run.bat`.
- **Dual Modes**: Hỗ trợ linh hoạt **Offline mode** (mặc định) hoặc **Online mode** (thông qua API bên ngoài).
- **Skill-gated Tools**: Tools được khoá sau hệ thống skill, chỉ được kích hoạt khi agent đọc file `SKILL.md`.
- **3-tier Context Compression**: Tự động quản lý bộ nhớ qua soft-trim, graceful summarization, và emergency compression.

---

## 2) Cấu trúc thư mục

```
Agent-01/
├── run.bat                     # Launcher duy nhất (Windows)
├── pyproject.toml              # Package metadata + tool config
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test config (alias của pyproject)
├── .env.example                # Env variable template
├── .gitignore                  # Ignore rules
├── README.md                   # Quick start
├── docs/
│   ├── BLUEPRINT_EN.md         # Tài liệu kiến trúc đầy đủ (English)
│   ├── BLUEPRINT_VI.md         # (file này) Tài liệu kiến trúc đầy đủ (Tiếng Việt)
│   ├── TUTORIAL_EN.md          # Hướng dẫn chạy & tham số (English)
│   └── TUTORIAL_VI.md          # Hướng dẫn chạy & tham số (Tiếng Việt)
├── src/
│   ├── agentforge/             # Core runtime (23 files)
│   ├── builtin_tools/          # Tool implementations (8 files: 7 modules + __init__)
│   └── tests/                  # Test suite (38 test files + conftest)
├── workspace/                  # Thư mục dữ liệu runtime
│   ├── IDENTITY.md             # Danh tính agent (đọc vào system prompt)
│   ├── SOUL.md                 # Tính cách, giá trị agent
│   ├── AGENT.md                # Hướng dẫn & tool contract cho agent
│   ├── USER.md                 # Thông tin/sở thích user
│   ├── skills/                 # Các thư mục định nghĩa skill
│   ├── sessions/               # Session JSON files
│   └── screenshots/            # Ảnh chụp màn hình browser
├── adb-mcp/                    # Tuỳ chọn: Tích hợp Photoshop/ADB
└── llama-server/               # Thư mục trống để giải nén file llama-server (chỉ track folder)
```

---

## 3) Kiến trúc runtime

### 3.1 Vòng lặp chính (Tool-calling loop)

```
User Input
    ↓
┌─────────────────────────────────────────────┐
│  Agent.run(user_input)                      │
│  ┌─────────────────────────────────┐        │
│  │ 1. Xây dựng system prompt       │        │
│  │    (ContextBuilder: runtime      │       │
│  │     header + bootstrap .md +     │       │
│  │     skills XML)                  │       │
│  │ 2. Xây dựng messages            │        │
│  │    (PromptBuilder → OpenAI msg)  │       │
│  │ 3. Gọi LLM                      │       │
│  │    (LLMInference.chat_completion)│       │
│  │ 4. Phân tích response           │        │
│  │    - Structured tool_calls? →    │       │
│  │      thực thi qua ToolLoop      │       │
│  │    - Fallback text parse? →      │       │
│  │      ToolCallParser (JSON+XML)   │       │
│  │    - Pure text? → trả về        │        │
│  │ 5. Thêm tool results            │        │
│  │ 6. Lặp cho đến khi text-only    │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
    ↓
Final Assistant Text → UI Output
```

### 3.2 Luồng dữ liệu chi tiết

1. `cli.py` là facade tương thích; parse/config nằm ở `cli_args.py`, wiring runtime nằm ở `cli_runtime.py`.
2. `run_interactive()` chạy vòng lặp REPL: đọc input → `Agent.run()` → hiển thị kết quả.
3. `Agent.run()`:
   - Gọi `_update_system_prompt()` (ContextBuilder lắp ráp từ workspace .md, skills XML, tools list).
   - Gọi `_build_messages()` (PromptBuilder phát sinh OpenAI-format messages).
   - Gọi `_run_model_once()` → `LLMInference.chat_completion()`.
   - Nếu có tool calls → `_execute_tool_calls()` → `ToolLoop.execute_tool()` → thêm results → lặp lại.
   - Nếu model trả text → return kết quả.
4. Session tự động lưu sau mỗi turn.

---

## 4) Module map — `src/agentforge/`

| File | Dòng | Vai trò |
|------|------|---------|
| `__init__.py` | 4 | Package metadata (`__version__ = "1.1.1"`) |
| `cli.py` | 33 | Facade tương thích (`main`, `run_interactive`) |
| `cli_args.py` | 157 | Parser + nạp env/config + mapping `InferenceConfig` |
| `cli_runtime.py` | 303 | Vòng lặp REPL, wiring components, kết nối backend |
| `agent_core.py` | 510 | Class `Agent`: vòng lặp điều phối, thực thi tool, kích hoạt skill |
| `llm_inference.py` | 779 | Class `LLMInference`: transport local/remote, streaming, compat fallback |
| `contracts.py` | 77 | Dataclasses chung: `ToolCall`, `AssistantMessage`, `ToolMessage`, `ChatCompletionResult`, `ProviderCapabilities` |
| `prompting.py` | 96 | `PromptBuilder`: xây dựng structured messages cho chat-completions API |
| `runtime_config.py` | 97 | Parse cấu hình runtime từ ENV, clamp giá trị timeout/chính sách shell |
| `tools.py` | 215 | `Tool`, `ToolResult`, `ToolRegistry`: định nghĩa tool + xuất schema tương thích OpenAI |
| `tool_loop.py` | 181 | `ToolLoop`: các bộ bảo vệ chống lặp (repeat, no-progress, ping-pong, global circuit breaker) |
| `tool_call_parser.py` | 168 | `ToolCallParser`: parser hai định dạng (JSON + XML) cho fallback |
| `tool_id.py` | 47 | `sanitize_tool_call_id`, `remap_tool_call_ids`: chuẩn hoá ID cho các provider nghiêm ngặt |
| `tool_mutation.py` | 69 | Heuristic phân loại tool call thay đổi dữ liệu (mutating) vs chỉ đọc (read-only) |
| `session.py` | 411 | `SessionManager`: trạng thái hội thoại bền vững, schema v3, migration + lineage continuation |
| `session_repair.py` | 113 | Sửa chữa transcript: chuẩn hoá tool_calls, ghép cặp tool results, chèn kết quả tổng hợp |
| `schema_normalizer.py` | 310 | Chuẩn hoá JSON Schema cho tương thích provider (Gemini, Anthropic, OpenAI) |
| `transcript_policy.py` | 218 | Làm sạch transcript theo provider, chuẩn hoá tool-call-id, sửa ghép cặp |
| `skills.py` | 188 | `SkillLoader`: khám phá skill 3 tầng (workspace > user_config > builtin), kích hoạt/huỷ kích hoạt |
| `context.py` | 103 | `ContextBuilder`: lắp ráp system prompt động từ workspace .md + trạng thái runtime |
| `summarizer.py` | 234 | `Summarizer`: nén context 3 tầng (soft-trim → graceful → emergency) |
| `model_output_renderer.py` | 641 | Renderer realtime tree-lane, style markdown, tự nhận diện light/dark |
| `ui.py` | 595 | `ChatUI`: lớp giao diện terminal bọc renderer, cầu nối callback stream, hiển thị tool/status |

---

## 5) Module map — `src/builtin_tools/` (7 modules)

| File | Dòng | Tên skill | Các tools |
|------|------|-----------|-----------|
| `file_ops.py` | 394 | File Operations | `write_file`, `list_directory`, `search_files`, `file_info`, `move_file`, `copy_file`, `rename_path`, `make_directory`, `find_duplicates` |
| `sys_ops.py` | 514 | System | `shell_command`, `process_list` |
| `web_ops.py` | 179 | Web Operations | `http_request`, `web_scrape` |
| `web_search.py` | 113 | WebSearch | `web_search` (scraping HTML DuckDuckGo) |
| `browser_tools.py` | 365 | Browser | `browser_navigate`, `browser_click`, `browser_type`, `browser_screenshot`, `browser_get_content`, `browser_evaluate`, `browser_wait`, `browser_scroll`, `browser_select`, `browser_reset_context`, `browser_close` |
| `computer_use_tools.py` | 275 | Computer Use Agents | `desktop_screenshot`, `desktop_move_mouse`, `desktop_click`, `desktop_type`, `desktop_key`, `desktop_scroll` |
| `photoshop_tools.py` | 159 | Photoshop | 53 tools qua Socket.IO → adb-mcp proxy → UXP Plugin |

### Bootstrap tools (được mã hoá cứng trong `agent_core.py`)

- `read_file` — Đọc file bất kỳ; cũng dùng để kích hoạt skill.

---

## 6) Hệ thống Skill (kiểu MMORPG)

### 6.1 Cơ chế

1. Khi khởi động, agent chỉ có 1 bootstrap tool: `read_file`.
2. `SkillLoader` quét `workspace/skills/` để tìm các thư mục chứa `SKILL.md`.
3. `skill_id` chuẩn hoá theo tên thư mục skill (định danh runtime ổn định).
4. System prompt chứa XML `<available_skills>` liệt kê các skill và trạng thái.
5. Agent muốn dùng tool của 1 skill → gọi `read_file` trên `SKILL.md` → `agent_core` phát hiện và tự động kích hoạt skill, đăng ký tools vào `ToolRegistry`.
6. Skill chưa kích hoạt **không liệt kê tên tool** trong system prompt (ngăn agent gọi tools chưa activate).

### 6.1.1 Model biết skill/tool qua đâu?

1. Skill được bơm vào system prompt bằng XML `<available_skills>`.
2. Tool callable được bơm theo từng request qua payload `tools=[...]` từ `ToolRegistry.to_openai_tools()`.
3. Sau khi activate skill, runtime rebuild prompt + tools payload, nên lượt model kế tiếp thấy tool mới ngay.

### 6.2 Độ ưu tiên 3 tầng

```
workspace/skills/  (cao nhất — ghi đè của user)
user_config_dir/   (giữa   — mặc định user)
builtin_dir/       (thấp nhất — mặc định đi kèm)
```

### 6.3 Định dạng file skill

```yaml
---
name: browser
description: Điều khiển trình duyệt headless hoặc hiển thị qua Playwright.
module: builtin_tools.browser_tools
tools:
  - browser_navigate
  - browser_click
  - browser_type
  # ...
---
# Hướng dẫn chi tiết cho LLM khi skill được kích hoạt
```

### 6.4 Các skill hiện tại (7 skills)

| Thư mục skill | Tên skill | Module |
|---------------|-----------|--------|
| `browser/` | Browser | `builtin_tools.browser_tools` |
| `file_operations/` | File Operations | `builtin_tools.file_ops` |
| `system/` | System | `builtin_tools.sys_ops` |
| `web_operations/` | Web Operations | `builtin_tools.web_ops` |
| `web_search/` | WebSearch | `builtin_tools.web_search` |
| `computer-use-agents/` | Computer Use Agents | `builtin_tools.computer_use_tools` |
| `photoshop/` | Photoshop | `builtin_tools.photoshop_tools` |

---

## 7) Chiến lược provider và tương thích

### 7.1 Hai chế độ (Provider)

| Chế độ | Kích hoạt | Backend |
|--------|-----------|---------|
| **Offline mode** | `PROVIDER=local` | Chạy 100% offline trên máy cá nhân bằng `llama-server.exe` với model GGUF. |
| **Online mode** | `PROVIDER=openai_compatible` | Dùng sức mạnh đám mây để gọi LLM qua endpoint API (ví dụ OpenAI, Anthropic, Google). |

### 7.2 Hợp đồng request chính

Payload gửi tới `/v1/chat/completions`:

- `model` — định danh model
- `messages` — lịch sử hội thoại (OpenAI message format)
- `temperature`, `top_p` — tham số lấy mẫu
- Giới hạn token:
  - `max_completion_tokens` cho OpenAI `o-series`
  - `max_tokens` cho model/provider khác
- Tuỳ chọn: `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`
- Điều khiển reasoning tuỳ chọn:
  - `reasoning_effort` (`low`, `medium`, `high`, `extra_high`)
  - AgentForge gửi `reasoning_effort` đúng theo config (chuẩn hoá dạng underscore).
    Nếu provider từ chối field này thì fallback loại đúng field đó và retry.

### 7.3 Bậc thang fallback (giảm cấp có kiểm soát)

Khi provider từ chối field, `LLMInference._apply_compat_payload_fallback()` retry theo thứ tự loại bỏ:

1. `tools` + `tool_choice` (+ `parallel_tool_calls`)
2. `parallel_tool_calls`
3. `response_format`
4. Fallback giới hạn token (`max_completion_tokens` ↔ `max_tokens`)
5. `reasoning_effort`
6. `stream`
7. `grammar`
8. `stop`

Số lần retry tối đa: `COMPAT_RETRY_LIMIT` (mặc định 8).

### 7.4 Phát hiện provider và chính sách transcript

`transcript_policy.py` tự động phát hiện loại provider từ base_url:

| Provider | Đặc điểm |
|----------|----------|
| `openai` | Làm sạch tool-call ID, sửa ghép cặp |
| `anthropic` | Bỏ tool results mồ côi |
| `google` | Chế độ tool-call ID nghiêm ngặt |
| `local` | Làm sạch tối thiểu |
| `other` | Chính sách chung |

---

## 8) Session và persistence

### 8.1 Session schema

- **Schema version**: `3`
- **Vị trí**: `workspace/sessions/{session_id}.json`
- **Tự động migration**: transcript cũ được migrate lên v3 khi load.
- **Lineage**: session continuation có thêm `previous_session_id`.
- **Sửa chữa**: `session_repair.py` chuẩn hoá các khối tool_call, ghép cặp tool results, chèn kết quả tổng hợp cho tool calls mồ côi.

### 8.2 Luồng lưu trữ

```
Lượt user → Agent.run() → SessionManager.add_message()
                        → _save() (ghi nguyên tử: .tmp → rename)
Tool call  → add_assistant_tool_calls() + add_tool_result()
             → _flush_pending_tool_results() (đảm bảo ghép cặp)
             → _save()
```

### 8.3 Phạm vi lưu trữ

- Trạng thái hội thoại bền vững được lưu trong `workspace/sessions/*.json`.
- Runtime không còn nạp subsystem bộ nhớ dài hạn.

---

## 9) Lắp ráp System Prompt

`ContextBuilder.build_system_prompt()` ghép các phần theo thứ tự:

1. **Runtime header** (lập trình): phiên bản Agent, thời gian, OS, đường dẫn workspace.
2. **Available Tools** (động): từ `ToolRegistry`.
3. **Skills XML** (động): từ `SkillLoader.build_skills_xml()`.
4. **Bootstrap files** (tĩnh): đọc từ workspace — `IDENTITY.md`, `SOUL.md`, `AGENT.md`, `USER.md`.

Các phần được nối bởi `\n\n---\n\n`.

---

## 10) Quản lý context window (Summarizer)

Mẫu nén 3 tầng:

| Tầng | Ngưỡng kích hoạt | Hành động |
|------|-------------------|-----------|
| 0.5 Soft-trim | 60% dung lượng | Cắt tỉa tool results dài (giữ đầu/cuối 500 ký tự, cắt giữa) |
| 1 Graceful | 70% dung lượng | Tóm tắt bằng LLM (ưu tiên), rồi nén transcript in-place và chèn context memory note |
| 2 Emergency | Lỗi tràn context | Giữ phần đuôi gần nhất theo ngưỡng động (thường 6–10 messages) + memory note |

Ngưỡng được tính theo `max_tokens × chars_per_token` (mặc định 4).

---

## 11) An toàn vòng lặp tool (ToolLoop)

| Bộ bảo vệ | Ngưỡng | Hành động |
|------------|--------|-----------|
| Phát hiện lặp chung | `max_repeats` (mặc định 3) | Chặn tool call trùng arguments |
| Chuỗi không tiến triển | `global_threshold` (mặc định 30) | Circuit breaker khi kết quả giống nhau |
| Ping-pong | `warning_threshold` (mặc định 10) | Phát hiện mẫu A→B→A→B |
| Giới hạn vòng lặp | `max_iterations` (mặc định từ launcher: 60) | Dừng vòng lặp |
| Timeout | `timeout` (mặc định 60s) | Dừng vòng lặp |

---

## 12) Mô hình bảo mật

### 12.1 Lệnh shell (`sys_ops.py`)

- **Mặc định theo danh sách cho phép**: chỉ cho phép các lệnh trong tập `ALLOWED_COMMANDS`.
- **Danh sách chặn ưu tiên**: `BLOCKED_COMMANDS` (rm, del, format, shutdown, v.v.) ghi đè danh sách cho phép.
- **Phân tích pipeline**: `_split_command_segments()` phân tích `|`, `||`, `&&`, `;` và xác thực từng phần.
- **Siết lệnh Python**: chặn thực thi inline qua `python/py` với `-c`, `-m`, stdin script, và cờ interactive.
- **Siết lệnh pip**: chặn các subcommand thay đổi hệ thống (`install`, `uninstall`, ...); chỉ cho phép nhóm lệnh đọc thông tin an toàn.
- **Sandbox workspace mặc định**: `shell_command` mặc định ép `cwd` trong workspace (`SHELL_WORKSPACE_ONLY=1`), có thể tắt chủ động bằng `SHELL_WORKSPACE_ONLY=0`.
- **Giới hạn đầu ra**: stdout 5000 ký tự, stderr 2000 ký tự.

### 12.5 Ghi file (`file_ops.py`)

- `write_file`, `move_file`, `copy_file`, `rename_path`, `make_directory`, `find_duplicates` đều bị giới hạn trong workspace.
- Path tương đối sẽ được resolve bên trong workspace.
- Path tuyệt đối nằm ngoài workspace sẽ bị chặn bằng lỗi `SECURITY[...]` (ví dụ `WRITE_OUTSIDE_WORKSPACE`).

### 12.6 Giới hạn tốc độ request LLM (`llm_inference.py`)

- Transport áp dụng `max_requests_per_minute` (mặc định `60`).
- Áp dụng cho cả request thường và request streaming.
- Khi vượt ngưỡng sẽ trả lỗi có kiểm soát, tránh vòng lặp request vô hạn.

### 12.2 Yêu cầu web (`web_ops.py`)

- **Bảo vệ SSRF**: chặn localhost, IP riêng, link-local, multicast.
- **Kiểm tra phân giải DNS**: phân giải hostname và chặn nếu đích là IP riêng.
- **Hạn chế scheme**: chỉ `http` và `https`.
- **Làm sạch ký tự điều khiển**: loại bỏ ký tự không in được từ response.

### 12.3 API keys

- **Không commit secrets**: `.env` bị gitignore, chỉ `.env.example` được theo dõi.
- **Truy cập key gián tiếp**: API key đọc qua tên env (`API_KEY_ENV`), runtime phân giải `os.environ[key_env_name]`.

### 12.4 Tools bị loại bỏ ở v1.1

- Built-in `calculator` và `message` đã bị xóa khỏi runtime và skill inventory.

---

## 13) Streaming và UI

### 13.1 Giao diện terminal (`ui.py`)

- **Hiển thị tree-lane tối giản**: luồng `│`, `├─`, `└─` nối input user, trạng thái xử lý, và output model.
- **Markdown stream thời gian thực**: output assistant được render markdown trực tiếp trong lúc token đang stream, không đợi cuối stream.
- **Thinking/reasoning stream**: token reasoning hiển thị trong lane khi đang xử lý.
- **Tool-call argument stream**: arguments của function được stream tăng dần trong code block lane và chuẩn hoá JSON đẹp khi hoàn tất.
- **Palette thích ứng**: tự nhận light/dark và override bằng `AGENTFORGE_UI_THEME=auto|dark|light`.
- **Rich tuỳ chọn**: có Rich thì render lane đầy đủ; không có Rich vẫn fallback cùng semantics lane.
- **Máy trạng thái pha**: `idle → started → reasoning|assistant → idle`.

### 13.2 Hệ thống callback

Dataclass `StreamCallbacks` trong `agent_core.py`:

| Callback | Mục đích |
|----------|----------|
| `on_token` | Token đầu ra từ assistant |
| `on_reasoning` | Token suy luận/thinking |
| `on_tool_call_start` | Bắt đầu stream khối tool call (`name`, `index`) |
| `on_tool_call_delta` | Chunk arguments tool-call theo thời gian thực (`index`, `token`) |
| `on_tool_call_end` | Kết thúc stream khối tool call (`index`) |
| `on_tool_call` | Callback tương thích cũ cho tool call không-stream (khi không có delta) |
| `on_tool_result` | Kết quả trả về từ tool |
| `on_stream_start` | Bắt đầu stream (UI chủ động kích hoạt) |
| `on_stream_end` | Kết thúc stream |
| `on_thinking_start/end` | Bắt đầu/kết thúc pha thinking |
| `on_skill_activated` | Skill được kích hoạt |

---

## 14) Cấu hình và tham số

### 14.1 Luồng cấu hình

User đặt biến ENV trước khi gọi `run.bat`. Launcher ánh xạ chúng sang CLI args:

```
Biến ENV (user đặt)
  ↓
run.bat defaults (if not defined → đặt mặc định)
  ↓
run.bat truyền tất cả xuống CLI entrypoint
  ↓
cli_args.py phân giải giá trị cuối cùng
```

Bypass: gọi trực tiếp `python -m agentforge.cli --flag value` sẽ ghi đè mọi thứ.

### 14.2 Tham số chính

| Tham số | Cờ CLI | Mặc định | Mô tả |
|---------|--------|----------|-------|
| `PROVIDER` | `--provider` | `local` | **Offline mode** (`local`) / **Online mode** (`openai_compatible`) |
| `SERVER_EXE` | `--server-exe` | (trong run.bat) | Đường dẫn llama-server.exe |
| `MODEL_PATH` | positional | (trong run.bat) | Đường dẫn model .gguf |
| `BASE_URL` | `--base-url` | `http://127.0.0.1:8080` | URL cho llama-server (local) hoặc Địa chỉ endpoint chat-completions compatible |
| `MODEL_ID` | `--model-id` | `local` | Định danh model mà nhà cung cấp yêu cầu |
| `API_KEY_ENV` | `--api-key-env` | `OPENAI_API_KEY` | Tên biến môi trường chứa API key |
| `CTX_SIZE` | `--ctx-size` | `16384` | Kích thước context window (token) |
| `GPU_LAYERS` | `--gpu-layers` | `-1` | Đẩy tối đa qua GPU (`-1` = tối đa) |
| `THREADS` | `--threads` | `0` | Hệ thống tự chọn số lượng CPU thread |
| `TEMPERATURE` | `--temp` | `0.1` | Độ ngẫu nhiên/sáng tạo của output |
| `TOP_P` | `--top-p` | `0.9` | Nucleus sampling |
| `TOP_K` | `--top-k` | `40` | Giới hạn tập token được xem mỗi bước |
| `REPEAT_PENALTY` | `--repeat-penalty` | `1.1` | Phạt lặp token |
| `SEED` | `--seed` | `-1` | Ngẫu nhiên mỗi lần (`-1`), hoặc số để tái lập |
| `REASONING_EFFORT` | `--reasoning-effort` | `low` | Mức reasoning: `low` / `medium` / `high` / `extra_high` |
| `MAX_TOKENS` | `--max-tokens` | `8192` | Giới hạn độ dài tối đa mỗi lần model trả lời |
| `HOST` | `--host` | `127.0.0.1` | Địa chỉ bind backend |
| `PORT` | `--port` | `8080` | Cổng backend |
| `BOOT_TIMEOUT` | `--boot-timeout` | `120` | Chờ server local khởi động (giây) |
| `HEALTH_TIMEOUT` | `--health-timeout` | `2` | Timeout từng lần health check (giây) |
| `REQUEST_TIMEOUT` | `--request-timeout` | `300` | Timeout mỗi request model (giây) |
| `SHUTDOWN_TIMEOUT` | `--shutdown-timeout` | `5` | Chờ local process tắt (giây) |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | `8` | Số lần thử lại khi provider không hợp payload |
| `MAX_REQUESTS_PER_MINUTE` | `--max-requests-per-minute` | `60` | Chặn request storm |
| `MAX_ITERATIONS` | `--max-iterations` | `60` | Giới hạn số vòng tool-call mỗi lượt |
| `MAX_REPEATS` | `--max-repeats` | `3` | Giới hạn lặp tool với cùng tham số |
| `AGENT_TIMEOUT` | `--agent-timeout` | `300` | Timeout tổng mỗi lượt (giây) |
| `WORKSPACE` | `--workspace` | `./workspace` | Thư mục làm việc của Agent |
| `AGENTFORGE_UI_THEME` | chỉ env | `auto` | Chế độ màu UI: `auto` / `dark` / `light` |
| `AGENTFORGE_BROWSER_HEADLESS` | chỉ env | `0` | `0`=hiển thị, `1`=ẩn |
| `AGENTFORGE_DESKTOP_CONTROL` | chỉ env | `1` | `1` bật desktop tools, `0` tắt |
| `TOOL_TIMEOUT_BROWSER_NAV_MS` | chỉ env | `60000` | Timeout `browser_navigate` (ms) |
| `TOOL_TIMEOUT_BROWSER_ACTION_MS` | chỉ env | `15000` | Timeout click/type/select/get_content (ms) |
| `TOOL_TIMEOUT_BROWSER_WAIT_MS` | chỉ env | `30000` | Timeout `browser_wait` (ms) |
| `TOOL_TIMEOUT_DESKTOP_ACTION_MS` | chỉ env | `5000` | Ngưỡng timeout thao tác desktop (ms) |
| `TOOL_TIMEOUT_DESKTOP_SCREENSHOT_S` | chỉ env | `15` | Ngưỡng timeout chụp desktop (giây) |
| `TOOL_TIMEOUT_WEB_REQUEST_S` | chỉ env | `30` | Timeout `http_request`/`web_scrape` (giây) |
| `TOOL_TIMEOUT_WEB_SEARCH_S` | chỉ env | `15` | Timeout `web_search` (giây) |
| `TOOL_TIMEOUT_PHOTOSHOP_S` | chỉ env | `30` | Timeout tool Photoshop (giây) |
| `TOOL_TIMEOUT_PROCESS_LIST_S` | chỉ env | `10` | Timeout tool `process_list` (giây) |
| `SHELL_WORKSPACE_ONLY` | chỉ env | `1` | `1` ép shell trong workspace; `0` tắt sandbox cwd |

---

## 15) Bộ test

### 15.1 Cấu hình

```ini
# pytest.ini / pyproject.toml
testpaths = src/tests
pythonpath = src
addopts = -q
```

### 15.2 Các file test (39 files = 38 tests + `conftest.py`)

| File | Phạm vi |
|------|---------|
| `conftest.py` | Fixtures dùng chung |
| `test_agent_fallback_parser_activation.py` | Kích hoạt fallback parser |
| `test_agent_session_continuation.py` | Hydrate session + đảm bảo graceful compaction in-place |
| `test_bootstrap_tools.py` | Đăng ký bootstrap tool (`read_file`) |
| `test_browser_locators_and_reset.py` | Locator browser + tool reset context |
| `test_cli_config_merge.py` | Logic gộp cấu hình CLI |
| `test_cli_env_file.py` | Tải file `.env` |
| `test_cli_required_loop_args.py` | Ràng buộc loop args bắt buộc (`max_iterations`, `max_repeats`, `agent_timeout`) |
| `test_cli_runtime_stream_lifecycle.py` | Vòng đời stream start/end trong runtime |
| `test_computer_use_tools.py` | Desktop tools (`desktop_*`) |
| `test_context_builder.py` | Lắp ráp ContextBuilder + xử lý lỗi đọc bootstrap |
| `test_contracts_and_registry.py` | Hợp đồng ToolCall, ToolRegistry |
| `test_docs_link_integrity.py` | Tính hợp lệ link tài liệu |
| `test_file_ops_organizer_tools.py` | Nhóm tool tổ chức file (`move/copy/rename/mkdir/duplicates`) |
| `test_file_ops_security.py` | Cưỡng chế sandbox workspace cho file ops |
| `test_integration_mock_provider.py` | Tích hợp đầy đủ với mock LLM |
| `test_llm_fallback.py` | Fallback tương thích LLM |
| `test_llm_local_process_spawn.py` | Spawn/quản lý vòng đời llama-server local |
| `test_llm_rate_limit.py` | Guard giới hạn request LLM/phút |
| `test_output_renderer.py` | Hành vi renderer đầu ra model |
| `test_prompting_builder.py` | Dựng/truncate structured messages trong PromptBuilder |
| `test_regression_callbacks_streaming.py` | Hồi quy callback streaming |
| `test_schema_provider_compat.py` | Chuẩn hoá schema theo provider |
| `test_security_tools.py` | Bảo mật shell/web |
| `test_session_append_guard.py` | Bảo vệ append session |
| `test_session_migration.py` | Migration schema session |
| `test_session_repair_helpers.py` | Tiện ích sửa chữa session |
| `test_skill_activation.py` | Luồng kích hoạt skill |
| `test_skill_loader_skill_md.py` | Parse/validate skill frontmatter |
| `test_skills_xml_payload.py` | Tính đúng đắn payload Skills XML |
| `test_smoke_modes.py` | Smoke tests chế độ local/remote |
| `test_summarizer_resilience.py` | Các trường hợp biên summarizer |
| `test_tool_async_execution.py` | Thực thi async tool trong runtime sync |
| `test_tool_call_parser_fallback.py` | Parser fallback tool call |
| `test_tool_loop_safety.py` | Bộ bảo vệ tool loop |
| `test_tool_mutation_policy.py` | Phân loại mutation |
| `test_tool_timeout_env_mapping.py` | Mapping timeout env cho browser/web/photoshop/desktop/sys |
| `test_transcript_policy.py` | Làm sạch transcript |
| `test_ui_safety.py` | An toàn UI |

### 15.3 Bộ lệnh kiểm tra chất lượng

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
cmd /c "set \"PROVIDER=openai_compatible\" && set \"BASE_URL=http://127.0.0.1:8080\" && set \"MODEL_ID=local\" && set \"EXTRA_ARGS=--help\" && run.bat"
```

---

## 16) Dependencies

### Runtime

| Package | Vai trò |
|---------|---------|
| `rich` | Định dạng terminal (có sẵn fallback tuỳ chọn) |
| `beautifulsoup4` | Scraping web |
| `playwright` | Tự động hoá trình duyệt |
| `pyautogui` | Desktop control tools (`desktop_*`) |
| `python-socketio` | Tools Photoshop (Socket.IO client) |
| `websocket-client` | Transport WebSocket cho socketio |
| `pyyaml` | Phân tích metadata skill |

### Dev

| Package | Vai trò |
|---------|---------|
| `pytest>=8` | Testing |
| `ruff>=0.6` | Linting |

---

## 17) Tuỳ chọn: Tích hợp adb-mcp

- **Thư mục**: `adb-mcp/` (trong repo, tuỳ chọn).
- **Mục đích**: Điều khiển Adobe Photoshop qua UXP plugin.
- **Kiến trúc**: `Agent → Socket.IO → adb-mcp proxy (Node.js) → UXP Plugin → Photoshop`.
- **Yêu cầu**: Adobe Photoshop 26.0+, UXP Developer Mode, `node adb-mcp/adb-proxy-socket/proxy.js`.
- **adb-mcp KHÔNG cần thiết để chạy core Agent-01**.

---

## 18) Các file khởi tạo workspace

Khi agent khởi động, `ContextBuilder` đọc các file từ workspace:

| File | Mục đích |
|------|----------|
| `IDENTITY.md` | Tên, vai trò, phiên bản, chế độ vận hành, bootstrap tools |
| `SOUL.md` | Tính cách, giá trị, phong cách giao tiếp |
| `AGENT.md` | Hướng dẫn, hợp đồng tool calling, quy tắc an toàn, luồng kích hoạt skill |
| `USER.md` | Thông tin/sở thích user |

Các file này là **nội dung tĩnh** — AI model/developer có thể tuỳ chỉnh.

---

## 19) CI workflow (hiện tại)

### Windows CI

```yaml
# .github/workflows/ci.yml
name: ci

on:
  push:
  pull_request:

jobs:
  windows-quality:
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m pip install ruff

      - name: Lint
        run: python -m ruff check src

      - name: Tests
        run: python -m pytest -q

      - name: Build check
        run: python -m compileall -q src

      - name: CLI smoke
        shell: pwsh
        run: |
          $env:PYTHONPATH = "src"
          python -m agentforge.cli --help

      - name: Launcher smoke
        shell: cmd
        run: |
          set PROVIDER=openai_compatible
          set BASE_URL=http://127.0.0.1:8080
          set MODEL_ID=local
          set EXTRA_ARGS=--help
          call run.bat
```

---

## 20) Design patterns và conventions

### 20.1 Sử dụng trong dự án

- **Hợp đồng message OpenAI**: Toàn bộ runtime dùng định dạng `messages` của OpenAI Chat Completions.
- **Structured-first, fallback-second**: Ưu tiên `tool_calls` có cấu trúc, fallback sang ToolCallParser khi provider không hỗ trợ.
- **Dual-output pattern**: Nhiều module sử dụng mẫu thiết kế dual-output cho kết quả công cụ.
- **ToolResult đầu ra kép**: `for_llm` (context cho LLM) và `for_user` (hiển thị cho user) phân biệt nội dung.
- **I/O file nguyên tử**: Session dùng ghi nguyên tử (ghi .tmp, rồi rename).

### 20.2 Quy ước viết mã

- **Python 3.10+**: dùng type hints, dataclasses.
- **Ruff** với `select = ["F"]` (chỉ flake8 pyflakes rules), bỏ qua `F401, F541, F841`.
- **Độ dài dòng**: 100 ký tự.
- **Logging**: `logging.getLogger(__name__)` trong mỗi module.
- **Xử lý lỗi**: fallback nhẹ nhàng, không crash runtime.

---

## 21) Lưu ý cho AI model/developer

1. **Khi sửa `run.bat`** phải chạy launcher smoke `cmd /c "set \"PROVIDER=openai_compatible\" && set \"BASE_URL=http://127.0.0.1:8080\" && set \"MODEL_ID=local\" && set \"EXTRA_ARGS=--help\" && run.bat"` để xác nhận launcher còn hoạt động.
2. **Mỗi tool mới** phải có: định nghĩa trong `builtin_tools/`, file skill `SKILL.md` trong `workspace/skills/`, và hàm `register()`.
3. **Test trước khi merge** — mọi thay đổi cần chạy `python -m pytest -q`.
4. **Không mã hoá cứng secrets** — dùng biến env.
5. **Module mới trong `agentforge/`** cần được import trong `cli.py` hoặc `agent_core.py` để nối vào runtime.
6. **Tương thích ngược session** — nếu thay đổi schema, tăng `SESSION_SCHEMA_VERSION` và thêm logic migration trong `migrate_session_payload()`.
7. **Tool schema** phải là JSON Schema hợp lệ với `type: "object"` ở top-level — `schema_normalizer.py` sẽ chuẩn hoá nhưng tốt nhất viết đúng từ đầu.

---

## 22) Nguồn tham chiếu

- PyPA `pyproject.toml`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- pip repeatable installs: https://pip.pypa.io/en/stable/topics/repeatable-installs/
- GitHub Actions Python: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- OpenAI Chat Completions: https://platform.openai.com/docs/api-reference/chat
- OpenAI migrate to Responses: https://platform.openai.com/docs/guides/migrate-to-responses
- OpenClaw concepts:
  - https://docs.openclaw.ai/concepts/model-providers
  - https://docs.openclaw.ai/concepts/model-failover
