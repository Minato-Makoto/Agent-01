# Agent-01 (AgentForge Runtime)

Windows-first AI agent runtime. Entry duy nhat cho user: `run.bat`.

## Quick start

1. Cai Python 3.10+.
2. Mo terminal tai root repo.
3. Chay:

```bat
run.bat
```

`run.bat` la launcher 1-file: tu kiem tra/install dependency, nhan tham so qua env, va chay `agentforge.cli`.

## Provider modes

- `PROVIDER=local`:
  - can `SERVER_EXE` (llama-server.exe)
  - can `MODEL_PATH` (.gguf)
- `PROVIDER=openai_compatible`:
  - can `BASE_URL`, `MODEL_ID`, `API_KEY_ENV`

## Browser visibility

- Hien browser de user view:
  - `set AGENTFORGE_BROWSER_HEADLESS=0`

## Quality checks

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
```

## Docs

- [Blueprint (EN)](docs/BLUEPRINT_EN.md)
- [Blueprint (VI)](docs/BLUEPRINT_VI.md)
- [Tutorial](docs/TUTORIAL.md)
- [Changelog](CHANGELOG.md)
