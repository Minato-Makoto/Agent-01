# Deployment (Windows-First)

## Deployment model

- Primary runtime: Windows host using `run.bat`.
- Backend modes:
  - `local`: llama.cpp server executable + GGUF model.
  - `openai_compatible`: remote OpenAI-compatible endpoint.
- `adb-mcp`: optional integration, not required for baseline deployment.

## Deterministic preparation

1. Install Python 3.10+.
2. Run `scripts\setup.bat`.
3. Configure runtime via:
   - environment variables, or
   - `run.bat` defaults, or
   - `--env-file`.
4. Validate launcher without starting backend:
   - `set CHECK_ONLY=1`
   - `run.bat`

## CI gates

Pipeline should run:

1. `python -m pip install -r requirements.txt`
2. `python -m pytest -q`
3. `python -m compileall -q src`
4. `set PYTHONPATH=src && python -m agentforge.cli --help`

## Release checklist

1. `scripts\test.bat` passes.
2. `scripts\build.bat` passes.
3. `CHECK_ONLY=1 run.bat` passes.
4. `CHANGELOG.md` updated (especially destructive changes).
5. `.env.example` updated for any new required env vars.
6. `README.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` consistent with runtime behavior.

## Rollback notes

1. Roll back to previous known-good commit/tag.
2. Restore previous `run.bat` and environment settings.
3. If session format changed, keep backups of `workspace/sessions/*.json`.
4. Re-run smoke checks:
   - `python -m pytest -q`
   - `CHECK_ONLY=1 run.bat`
