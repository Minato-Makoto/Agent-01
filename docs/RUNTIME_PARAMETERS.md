# Runtime Parameters Guide (v1.0.1)

Canonical mapping between `run.bat`, CLI flags, and `InferenceConfig`.

## Precedence

1. `InferenceConfig` defaults in code.
2. CLI overrides for flags you pass.
3. `run.bat` values (because `run.bat` builds CLI args).

## Mapping

| run.bat | CLI flag | InferenceConfig | Notes |
|---|---|---|---|
| `CTX_SIZE` | `--ctx-size` | `n_ctx` | Context window |
| `GPU_LAYERS` | `--gpu-layers` | `n_gpu_layers` | GPU offload layers |
| `THREADS` | `--threads` | `n_threads` | CPU threads |
| `TEMPERATURE` | `--temp` | `temperature` | Sampling temperature |
| `TOP_P` | `--top-p` | `top_p` | Nucleus sampling |
| `TOP_K` | `--top-k` | `top_k` | Top-k sampling |
| `REPEAT_PENALTY` | `--repeat-penalty` | `repeat_penalty` | Repetition control |
| `SEED` | `--seed` | `seed` | Determinism (`-1` random) |
| `REASONING_FORMAT` | `--reasoning-format` | `reasoning_format` | Non-standard provider extension |
| `REASONING_EFFORT` | `--reasoning-effort` | `reasoning_effort` | OpenAI reasoning control |
| `MAX_TOKENS` | `--max-tokens` | `max_tokens` | Logical output token cap |
| `HOST` | `--host` | `host` | Local bind host |
| `PORT` | `--port` | `port` | Local bind port |
| `BOOT_TIMEOUT` | `--boot-timeout` | `boot_timeout_s` | Local startup timeout |
| `HEALTH_TIMEOUT` | `--health-timeout` | `health_timeout_s` | Health-check timeout |
| `REQUEST_TIMEOUT` | `--request-timeout` | `request_timeout_s` | Inference request timeout |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | `compat_retry_limit` | Compatibility retry limit |
| `MODEL_ID` | `--model-id` | `model_id` | Model identifier in payload |

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
