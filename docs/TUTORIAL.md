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
| `REASONING_FORMAT` | `--reasoning-format` | Reasoning field cho local/third-party | `auto`, `none` |
| `REASONING_EFFORT` | `--reasoning-effort` | Muc reasoning cho OpenAI-style | `low`, `medium` |
| `MAX_TOKENS` | `--max-tokens` | Tran token output logic | `2048`, `8192` |
| `HOST` | `--host` | Dia chi bind backend local | `127.0.0.1` |
| `PORT` | `--port` | Cong backend local | `8080`, `9000` |
| `BOOT_TIMEOUT` | `--boot-timeout` | Timeout khoi dong backend local | `120`, `180` |
| `HEALTH_TIMEOUT` | `--health-timeout` | Timeout health check | `2`, `5` |
| `REQUEST_TIMEOUT` | `--request-timeout` | Timeout 1 request inference | `300`, `600` |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | So lan retry fallback compatibility | `8`, `12` |
| `EXTRA_ARGS` + `--max-requests-per-minute` | `--max-requests-per-minute` | Tran request LLM moi phut (chong runaway loop) | `--max-requests-per-minute 60` |
| `WORKSPACE` | `--workspace` | Thu muc du lieu runtime | `%~dp0workspace` |
| `EXTRA_ARGS` | append raw args | Nhoi them args tuy bien | `--verbose` |
| `AGENTFORGE_BROWSER_HEADLESS` | env runtime | `0` hien cua so browser, `1` chay an | `0` |

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

### 5.4 Browser tools hien cua so de user xem

```bat
set AGENTFORGE_BROWSER_HEADLESS=0
run.bat
```

## 6) Troubleshooting

1. `llama-server.exe not found`: kiem tra `SERVER_EXE`.
2. `model file not found`: kiem tra `MODEL_PATH`.
3. Remote mode loi auth: kiem tra `API_KEY_ENV` va bien key that su ton tai.
4. Treo/lau: tang `BOOT_TIMEOUT` hoac `REQUEST_TIMEOUT`.
5. Output lap: giam `TEMPERATURE`, tang nhe `REPEAT_PENALTY`.

## 7) Lenh quality can ban

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
```

## 8) Optional `adb-mcp`

- `adb-mcp` la tuy chon, khong bat buoc de run core Agent-01.
- Neu can workflow Photoshop/ADB, cai dat va chay rieng theo huong dan trong thu muc `adb-mcp`.
