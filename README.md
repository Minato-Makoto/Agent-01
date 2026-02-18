# Agent-01 (AgentForge Runtime)

Windows-first AI agent runtime with structured tool-calling and OpenAI-compatible transport.

## Platform

- Supported OS: Windows (launcher is `.bat`-first by design).
- Python: 3.10+.
- Entry command: `run.bat`.

## One-command workflows

- Setup: `scripts\setup.bat`
- Lint: `scripts\lint.bat`
- Test: `scripts\test.bat`
- Build check: `scripts\build.bat`
- Start (dev): `scripts\start-dev.bat`
- Start (prod-style, no auto setup): `scripts\start-prod.bat`
- Local review routine: `scripts\review-local.bat`

## Quick start

1. `scripts\setup.bat`
2. Configure env values:
   - edit `run.bat` defaults, or
   - set environment variables before calling `run.bat`, or
   - use `python -m agentforge.cli run --env-file .env`.
3. Run `run.bat`

Smoke-check launcher only (no backend/model startup):

```bat
set CHECK_ONLY=1
run.bat
```

## Local mode

- `PROVIDER=local`
- Required:
  - `SERVER_EXE` -> `llama-server.exe`
  - `MODEL_PATH` -> `.gguf` model path

## Remote mode

- `PROVIDER=openai_compatible`
- Required:
  - `BASE_URL`
  - `MODEL_ID`
  - `API_KEY_ENV` (env var name containing API key)

OpenAI API key preflight is enforced when `BASE_URL` points to `api.openai.com`.

## Optional `adb-mcp`

`adb-mcp` is optional and intentionally not required for base runtime startup.
If needed, install and run it separately from `adb-mcp/` following its own guide.

## Runtime overview

```text
User input
  -> Agent core
  -> Chat Completions request
  -> assistant tool calls (if any)
  -> local tool execution
  -> tool result messages
  -> final assistant response
```

Fallback text parser (`<tool_call>...</tool_call>`) is used only when structured tool-calling is unavailable or provider compatibility fallback is active.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Runbook](docs/RUNBOOK.md)
- [Model Compatibility](docs/MODEL_COMPATIBILITY.md)
- [Runtime Parameters](docs/RUNTIME_PARAMETERS.md)
- [Migration Guide](docs/MIGRATION.md)
- [Changelog](CHANGELOG.md)
