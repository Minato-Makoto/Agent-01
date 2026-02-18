# Runbook

## Daily commands

- Setup machine: `scripts\setup.bat`
- Lint source: `scripts\lint.bat`
- Run tests: `scripts\test.bat`
- Build sanity check: `scripts\build.bat`
- Start runtime: `run.bat`
- Local review pass before merge: `scripts\review-local.bat`

## Startup troubleshooting

### `Workspace not found`

- Ensure `WORKSPACE` points to an existing folder.
- Default: `<repo>\workspace`.

### `llama-server.exe not found`

- Set `SERVER_EXE` correctly for local mode.

### `MODEL_PATH is required` or model not found

- Set `MODEL_PATH` to a valid `.gguf` path for local mode.

### OpenAI-compatible remote mode fails

- Check `BASE_URL`, `MODEL_ID`.
- If using OpenAI endpoint, ensure env var from `API_KEY_ENV` exists.

## Health/smoke routine

1. `python -m pytest -q`
2. `python -m compileall -q src`
3. `set PYTHONPATH=src && python -m agentforge.cli --help`
4. `set CHECK_ONLY=1 && run.bat`

## Optional `adb-mcp` integration

- Core runtime does not require `adb-mcp`.
- To enable Photoshop/ADB workflows, install and run `adb-mcp` separately.
