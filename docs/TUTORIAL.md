# TUTORIAL

Huong dan chay Agent-01 theo kieu Windows-first, 1 file launcher (`run.bat`).

## 1) Yeu cau

- Windows
- Python 3.10+
- Repo da duoc clone/day du file

## 2) Chay nhanh

Mo `cmd` hoac PowerShell tai root repo, sau do:

```bat
run.bat
```

`run.bat` se:

1. Tu tao `workspace` neu chua co.
2. Kiem tra/install dependency Python neu may chua co.
3. Chay `python -m agentforge.cli ...` voi bo tham so da khai bao trong file.

## 3) Chinh tham so ngay trong `run.bat`

Tat ca tham so nam trong khoi `if not defined ... set ...`.
Ban co 2 cach:

1. Sua truc tiep default trong `run.bat`.
2. Override tam thoi bang `set VAR=value` roi goi `run.bat`.

## 4) Mapping tham so (co giai thich + vi du)

| Bien trong run.bat | Mapping CLI | Y nghia | Vi du |
|---|---|---|---|
| `PROVIDER` | `--provider` | Che do backend (`local`/`openai_compatible`) | `local` |
| `SERVER_EXE` | `--server-exe` | Duong dan `llama-server.exe` (local) | `D:\tools\llama-server.exe` |
| `MODEL_PATH` | positional `model` | Duong dan model `.gguf` (local) | `D:\models\qwen.gguf` |
| `BASE_URL` | `--base-url` | URL endpoint remote | `https://api.openai.com/v1` |
| `MODEL_ID` | `--model-id` | Model ID gui len endpoint | `gpt-5-mini` |
| `API_KEY_ENV` | `--api-key-env` | Ten env chua API key | `OPENAI_API_KEY` |
| `CTX_SIZE` | `--ctx-size` | Kich thuoc context | `8192`, `16384` |
| `GPU_LAYERS` | `--gpu-layers` | So layer offload GPU (`-1` = toi da) | `-1`, `20` |
| `THREADS` | `--threads` | So CPU threads (`0` = auto) | `0`, `8` |
| `TEMPERATURE` | `--temp` | Do ngau nhien output | `0.1`, `0.7` |
| `TOP_P` | `--top-p` | Nucleus sampling | `0.9`, `0.95` |
| `TOP_K` | `--top-k` | Gioi han so token candidate | `40`, `80` |
| `REPEAT_PENALTY` | `--repeat-penalty` | Phat lap token | `1.1`, `1.2` |
| `SEED` | `--seed` | Seed random (`-1` = random) | `-1`, `42` |
| `REASONING_EFFORT` | `--reasoning-effort` | Muc reasoning thong nhat | `low`, `medium`, `high`, `extra_high` |
| `MAX_TOKENS` | `--max-tokens` | Tran token output logic | `2048`, `8192` |
| `HOST` | `--host` | Dia chi bind backend local | `127.0.0.1` |
| `PORT` | `--port` | Cong backend local | `8080`, `9000` |
| `BOOT_TIMEOUT` | `--boot-timeout` | Timeout khoi dong backend local | `120`, `180` |
| `HEALTH_TIMEOUT` | `--health-timeout` | Timeout health check | `2`, `5` |
| `REQUEST_TIMEOUT` | `--request-timeout` | Timeout 1 request inference | `300`, `600` |
| `SHUTDOWN_TIMEOUT` | `--shutdown-timeout` | Timeout dung local process an toan | `5`, `10` |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | So lan retry fallback compatibility | `8`, `12` |
| `MAX_REQUESTS_PER_MINUTE` | `--max-requests-per-minute` | Tran request LLM moi phut (chong runaway loop) | `60`, `120` |
| `MAX_ITERATIONS` | `--max-iterations` | Gioi han vong loop agent moi turn | `10`, `20` |
| `MAX_REPEATS` | `--max-repeats` | Gioi han lap lai tool call giong nhau | `3`, `5` |
| `AGENT_TIMEOUT` | `--agent-timeout` | Timeout toan bo loop agent (giay) | `300`, `600` |
| `WORKSPACE` | `--workspace` | Thu muc du lieu runtime | `%~dp0workspace` |
| `EXTRA_ARGS` | append raw args | Nhoi them args tuy bien | `--verbose` |
| `AGENTFORGE_UI_THEME` | env runtime | Chon palette UI terminal (`auto`/`dark`/`light`) | `auto` |
| `AGENTFORGE_BROWSER_HEADLESS` | env runtime | `0` hien cua so browser, `1` chay an | `0` |
| `TOOL_TIMEOUT_BROWSER_NAV_MS` | env runtime | Timeout navigate browser (ms) | `30000` |
| `TOOL_TIMEOUT_BROWSER_ACTION_MS` | env runtime | Timeout click/type/select/get_content (ms) | `5000` |
| `TOOL_TIMEOUT_BROWSER_WAIT_MS` | env runtime | Timeout browser_wait (ms) | `10000` |
| `TOOL_TIMEOUT_WEB_REQUEST_S` | env runtime | Timeout `http_request`/`web_scrape` (s) | `30` |
| `TOOL_TIMEOUT_WEB_SEARCH_S` | env runtime | Timeout `web_search` (s) | `15` |
| `TOOL_TIMEOUT_PHOTOSHOP_S` | env runtime | Timeout tool Photoshop qua proxy (s) | `30` |
| `TOOL_TIMEOUT_PROCESS_LIST_S` | env runtime | Timeout tool `process_list` (s) | `10` |
| `SHELL_WORKSPACE_ONLY` | env runtime | `1`: mac dinh chi cho shell trong workspace | `1`, `0` |

Luu y reasoning:
- Runtime chi gui `REASONING_EFFORT` (khong con dung `REASONING_FORMAT`).
- Gia tri duoc chuan hoa ve 4 muc: `low`, `medium`, `high`, `extra_high`.
- `reasoning_effort` la hint; backend co the bo qua neu khong ho tro.

## 5) Preset mau

### 5.1 Local coding on dinh

```bat
set PROVIDER=local
set CTX_SIZE=16384
set TEMPERATURE=0.1
set TOP_P=0.9
set TOP_K=40
set REPEAT_PENALTY=1.1
set MAX_TOKENS=4096
run.bat
```

### 5.2 Local may yeu / VRAM thap

```bat
set PROVIDER=local
set MODEL_PATH=D:\models\qwen.gguf
set CTX_SIZE=8192
set GPU_LAYERS=20
set THREADS=4
set MAX_TOKENS=2048
run.bat
```

### 5.3 Remote OpenAI-compatible

```bat
set PROVIDER=openai_compatible
set BASE_URL=https://api.openai.com/v1
set MODEL_ID=gpt-5-mini
set API_KEY_ENV=OPENAI_API_KEY
set OPENAI_API_KEY=YOUR_KEY
set REASONING_EFFORT=medium
run.bat
```

### 5.4 Safe mode shell (workspace-only)

```bat
set SHELL_WORKSPACE_ONLY=1
run.bat
```

### 5.5 Browser tools hien cua so de user xem

```bat
set AGENTFORGE_BROWSER_HEADLESS=0
run.bat
```

## 6) Troubleshooting

1. `MODEL_PATH is required when PROVIDER=local`: dat `MODEL_PATH` truoc khi chay.
2. `llama-server.exe not found`: kiem tra `SERVER_EXE`.
3. `model file not found`: kiem tra `MODEL_PATH`.
4. `SECURITY[CWD_OUTSIDE_WORKSPACE]`: shell dang bi sandbox workspace-only (`SHELL_WORKSPACE_ONLY=1`).
5. Neu can cho phep cwd ben ngoai workspace, dat tam: `set SHELL_WORKSPACE_ONLY=0`.
6. Remote mode loi auth: kiem tra `API_KEY_ENV` va bien key that su ton tai.
7. Treo/lau: tang `BOOT_TIMEOUT`/`REQUEST_TIMEOUT` hoac timeout tool phu hop.
8. Output lap: giam `TEMPERATURE`, tang nhe `REPEAT_PENALTY`.

## 7) Lenh quality can ban

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
```

## 8) Optional `adb-mcp`

- `adb-mcp` la tuy chon, khong bat buoc de run core Agent-01.
- Neu can workflow Photoshop/ADB, cai dat va chay rieng theo huong dan trong thu muc `adb-mcp`.
