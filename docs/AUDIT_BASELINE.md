# Audit Baseline (Pre-Refactor)

Date: 2026-02-18
Scope: `src/agentforge`, `src/builtin_tools`, root runtime files.

## Repo Map

- Runtime entry:
  - `run.bat` (Windows launcher)
  - `python -m agentforge.cli run ...`
- Core package:
  - `src/agentforge` (agent loop, inference, session, skills, UI)
- Built-in skills/tools:
  - `src/builtin_tools`
- Tests:
  - `src/tests`
- Optional integration:
  - `adb-mcp` (kept optional, install by guide)

## Baseline Checks

- `python -m pytest -q`: pass
- `python -m compileall -q src`: pass
- `python -m agentforge.cli --help`: requires `PYTHONPATH=src`

## Priority Problems

1. Git metadata missing (`.git` absent before this baseline).
2. Source tree contains tracked artifacts (`__pycache__/*.pyc`).
3. No standard Python project metadata (`pyproject.toml`) and no quality tooling config.
4. `run.bat` performs runtime dependency installation; setup/run responsibilities are coupled.
5. Several core modules use broad exception swallowing or silent fallback paths.
6. `llm_inference.py`, `cli.py`, `agent_core.py`, `ui.py` are oversized and mix concerns.
7. Env/config loading is not centralized (`--env-file` missing).
8. Missing coverage on selected modules (`summarizer`, `session_repair`, `tool_mutation`, `ui`).

## Refactor Direction

- Source-first normalization for all files in `src/agentforge`.
- Preserve Windows-first launch flow and current public CLI shape.
- Keep `adb-mcp` optional and isolated from core runtime assumptions.
- Apply quality gates after each major slice.
