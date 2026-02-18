# Runtime Parameters Guide (v1.0.1)

Canonical mapping between `run.bat`, CLI flags, and `InferenceConfig`.

## Precedence

1. `InferenceConfig` defaults in code.
2. CLI overrides for flags you pass.
3. `run.bat` values (because `run.bat` builds CLI args).

## Mapping (giải thích + ví dụ)

| run.bat | CLI flag | InferenceConfig | Giải thích | Ví dụ |
|---|---|---|---|---|
| `CTX_SIZE` | `--ctx-size` | `n_ctx` | Kích thước context; càng lớn càng tốn RAM/VRAM | `8192`, `16384` |
| `GPU_LAYERS` | `--gpu-layers` | `n_gpu_layers` | Số layer offload sang GPU (`-1` = tối đa) | `-1`, `20`, `0` |
| `THREADS` | `--threads` | `n_threads` | Số thread CPU cho backend local (`0` = auto) | `0`, `4`, `8` |
| `TEMPERATURE` | `--temp` | `temperature` | Độ ngẫu nhiên; thấp thì ổn định hơn | `0.1`, `0.2`, `0.7` |
| `TOP_P` | `--top-p` | `top_p` | Nucleus sampling, giới hạn xác suất tích lũy | `0.9`, `0.95` |
| `TOP_K` | `--top-k` | `top_k` | Giới hạn số token candidate mỗi bước | `40`, `80` |
| `REPEAT_PENALTY` | `--repeat-penalty` | `repeat_penalty` | Phạt lặp token để giảm lặp lại câu | `1.05`, `1.1`, `1.2` |
| `SEED` | `--seed` | `seed` | Hạt giống random (`-1` = random mỗi lần) | `-1`, `42` |
| `REASONING_FORMAT` | `--reasoning-format` | `reasoning_format` | Trường reasoning cho provider local/third-party | `auto`, `none` |
| `REASONING_EFFORT` | `--reasoning-effort` | `reasoning_effort` | Mức reasoning cho provider OpenAI-style | `low`, `medium`, `high` |
| `MAX_TOKENS` | `--max-tokens` | `max_tokens` | Trần token output logic | `2048`, `4096`, `8192` |
| `HOST` | `--host` | `host` | Địa chỉ bind server local | `127.0.0.1`, `0.0.0.0` |
| `PORT` | `--port` | `port` | Cổng server local | `8080`, `9000` |
| `BOOT_TIMEOUT` | `--boot-timeout` | `boot_timeout_s` | Timeout chờ local backend khởi động | `120`, `180` |
| `HEALTH_TIMEOUT` | `--health-timeout` | `health_timeout_s` | Timeout cho health check từng lần | `2`, `5` |
| `REQUEST_TIMEOUT` | `--request-timeout` | `request_timeout_s` | Timeout cho 1 request inference | `300`, `600` |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | `compat_retry_limit` | Số lần retry khi fallback compatibility | `8`, `12` |
| `MODEL_ID` | `--model-id` | `model_id` | Tên model gửi trong payload remote | `gpt-5-mini`, `local` |

## Launcher-only flags (không đi qua `InferenceConfig`)

| run.bat | Meaning | Default |
|---|---|---|
| `SHOW_BANNER` | Hiện header launcher | `0` |
| `AUTO_SETUP` | Tự gọi `scripts\setup.bat` trước khi chạy | `1` |
| `CHECK_ONLY` | Chỉ validate launcher, không khởi chạy model/backend | `0` |
| `NO_PAUSE` | Không dừng `pause` sau khi thoát | `0` |
| `AGENTFORGE_BROWSER_HEADLESS` | Browser tools chạy ẩn (`1`) hoặc hiện cửa sổ (`0`) | `0` |
| `WORKSPACE` | Thư mục workspace runtime | `<repo>\workspace` |
| `EXTRA_ARGS` | Nối thêm CLI args tùy ý | `(empty)` |

### `NO_PAUSE` dùng để làm gì?

- `NO_PAUSE=0` (mặc định): script dừng ở cuối bằng `pause`, tiện xem lỗi khi chạy bằng double-click.
- `NO_PAUSE=1`: script thoát ngay khi xong, phù hợp chạy trong terminal, CI, hoặc script tự động.

## Token-cap routing rule

`MAX_TOKENS` is a logical cap. Runtime maps it by provider/model:

1. OpenAI `o-series` model ID -> send `max_completion_tokens`.
2. Other models/providers -> send `max_tokens`.
3. If endpoint rejects chosen field, runtime retries with the alternate field.

## Provider mode flags

| run.bat | CLI flag | Meaning |
|---|---|---|
| `PROVIDER` | `--provider` | `local` or `openai_compatible` |
| `SERVER_EXE` | `--server-exe` | llama-server binary path |
| `MODEL_PATH` | positional `model` | GGUF model path |
| `BASE_URL` | `--base-url` | Remote endpoint base URL |
| `API_KEY_ENV` | `--api-key-env` | Env var name containing bearer token |

If `BASE_URL` resolves to `api.openai.com`, API key in `API_KEY_ENV` is mandatory.

## Recommended defaults

1. Coding precision: `TEMPERATURE=0.1`, `TOP_P=0.9`, `TOP_K=40`.
2. Deterministic debug: `TEMPERATURE=0.0`, `SEED=42`.
3. Low-resource mode: reduce `CTX_SIZE` and `MAX_TOKENS`.

## How to tune trực tiếp trong `run.bat`

Chỉnh khối `if not defined ... set ...` trong `run.bat` hoặc override bằng env trước khi gọi `run.bat`.

Ví dụ override tạm thời trong `cmd`:

```bat
set PROVIDER=openai_compatible
set BASE_URL=https://api.openai.com/v1
set MODEL_ID=gpt-5-mini
set REASONING_EFFORT=medium
set CHECK_ONLY=0
run.bat
```

Ví dụ chỉ kiểm tra launcher:

```bat
set CHECK_ONLY=1
set NO_PAUSE=1
run.bat
```

## Preset mẫu cho `run.bat`

### Local coding ổn định

```bat
set PROVIDER=local
set CTX_SIZE=16384
set TEMPERATURE=0.1
set TOP_P=0.9
set TOP_K=40
set REPEAT_PENALTY=1.1
set MAX_TOKENS=4096
```

### Local máy yếu / VRAM thấp

```bat
set PROVIDER=local
set CTX_SIZE=8192
set GPU_LAYERS=20
set THREADS=4
set MAX_TOKENS=2048
set TEMPERATURE=0.2
```

### Remote OpenAI-compatible

```bat
set PROVIDER=openai_compatible
set BASE_URL=https://api.openai.com/v1
set MODEL_ID=gpt-5-mini
set API_KEY_ENV=OPENAI_API_KEY
set REASONING_EFFORT=medium
set REQUEST_TIMEOUT=300
```

### Browser tools hiện cửa sổ cho user xem

```bat
set AGENTFORGE_BROWSER_HEADLESS=0
run.bat
```

## Troubleshooting

1. Rejected optional params: runtime auto-degrades payload.
2. Token-cap param rejected: runtime auto-switches `max_tokens`/`max_completion_tokens`.
3. Timeouts: increase `REQUEST_TIMEOUT` or `BOOT_TIMEOUT`.
4. Repetitive outputs: increase `REPEAT_PENALTY` slightly.
5. Tool-call quality issues: lower `TEMPERATURE` and use function-calling-capable models.

## Sync rule

Any new runtime parameter must be updated in:

1. `src/agentforge/llm_inference.py`
2. `src/agentforge/cli.py`
3. `run.bat`
4. docs and tests (`src/tests/test_cli_config_merge.py` minimum)
