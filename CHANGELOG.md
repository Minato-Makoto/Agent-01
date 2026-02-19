# Changelog

## [Unreleased]

### Changed
- Enabled Markdown rendering for assistant output in Rich terminal UI (`src/agentforge/ui.py`).
- Removed long-term memory injection from system prompt assembly.
- Restored `src/agentforge/llm_inference.py` as a single-file transport module (no split inference package).
- Split CLI responsibilities:
  - `src/agentforge/cli_args.py` for parser/env/config resolution
  - `src/agentforge/cli_runtime.py` for REPL/runtime wiring
  - `src/agentforge/cli.py` kept as compatibility facade.
- `Tool.execute(...)` now supports awaitable return values in sync runtime (enables gradual adoption of async tool implementations).
- Standardized tool exception handling with traceable error envelopes (`ToolResult.from_exception(...)`) across core builtin tools.
- Strengthened typing in session persistence path:
  - `SessionMessage.to_dict()`
  - `SessionMessage.to_transcript_entry()`
  - `SessionMessage.from_dict(...)`
- Expanded regression coverage for critical runtime paths:
  - `context.py`
  - `prompting.py`
  - skill activation to real tool execution
- Standardized ignore policy for runtime-generated artifacts (`workspace/sessions`, `workspace/screenshots`, logs), local environment files, and local runtime binaries/models.
- Reworked `run.bat` to a single-file Windows launcher:
  - removed hidden/banner toggles and extra control flags
  - removed dependency on helper scripts (`scripts\\setup.bat`)
  - keeps parameter comments + examples directly inside the launcher
- Added optional CLI `--env-file` support for centralized environment loading.
- Added project metadata/config in `pyproject.toml` and Windows CI workflow (`.github/workflows/ci.yml`).
- Consolidated documentation into:
  - `docs/BLUEPRINT_EN.md`
  - `docs/BLUEPRINT_VI.md`
  - `docs/TUTORIAL.md`
- `adb-mcp` is now kept in-repo as optional integration (not required for base runtime startup).
- Enforced line-ending policy with `.gitattributes`:
  - `*.bat` uses CRLF for `cmd.exe` compatibility
  - `*.py`/`*.md` normalized to LF in repo index.
- Hardened `run.bat`:
  - removed machine-specific default model path
  - local mode now fails fast with actionable `MODEL_PATH` guidance
  - added explicit parameter map and runtime profiles directly in launcher comments.
- Added centralized runtime env parser: `src/agentforge/runtime_config.py`.
- Added runtime CLI overrides:
  - `--shutdown-timeout`
  - `--max-iterations`
  - `--max-repeats`
  - `--agent-timeout`
- Removed hardcoded tool timeouts by wiring env-driven defaults:
  - browser, web request/search, Photoshop, process-list.
- `shell_command` now defaults to workspace-only cwd sandbox (`SHELL_WORKSPACE_ONLY=1`, opt-out with `0`).
- Refactored (without splitting file) `llm_inference.py` HTTP request construction to reduce duplication and improve debug traceability.
- Expanded regression gates:
  - CRLF invariant + real `run.bat` smoke test
  - timeout env mapping tests across key tools
  - shell workspace sandbox policy tests
  - agent loop CLI override test.
- CI now executes launcher smoke (`run.bat` with remote help mode) on Windows.

### Removed
- Removed persistent memory feature modules:
  - `src/agentforge/memory.py`
  - `src/builtin_tools/memory_tools.py`
- Removed memory command and memory-specific tests:
  - `src/tests/test_memory_store.py`
  - `src/tests/test_context_memory_format.py`
- Deleted generated Python cache artifacts from `src/**/__pycache__` and `.pytest_cache`.
  - Reason: generated runtime files are non-source artifacts and caused noisy audits.
  - Impact: no runtime behavior change; caches are regenerated automatically.
- Deleted helper launcher wrappers under `scripts/`.
  - Reason: launcher flow was over-split and conflicted with Windows-only single-file run requirement.
  - Impact: all startup should use `run.bat`; quality gates use direct Python commands.
- Deleted legacy docs:
  - `docs/AUDIT_BASELINE.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEPLOYMENT.md`
  - `docs/MIGRATION.md`
  - `docs/MODEL_COMPATIBILITY.md`
  - `docs/RUNBOOK.md`
  - `docs/RUNTIME_PARAMETERS.md`
  - Reason: merged into `docs/BLUEPRINT.md` and `docs/TUTORIAL.md` to remove duplication.
  - Impact: docs links must point to the two new files.

## [1.0.1] - 2026-02-17

### Added
- OpenAI-aligned `reasoning_effort` support across config, CLI, runtime, and launcher.
- API-key preflight validation for OpenAI base URL in remote mode.
- Production readiness report: `PRODUCTION_READINESS_AUDIT_2026-02-17.md`.

### Changed
- Terminal UI redesigned to ASCII-first presentation while preserving streaming callbacks.
- Provider-aware reasoning parameter routing:
  - OpenAI/OpenAI-compatible path prefers `reasoning_effort`.
  - Non-OpenAI provider path keeps `reasoning_format`.
- Core docs and workspace guidance rewritten for consistency and operational clarity.

### Fixed
- Avoid sending `reasoning_format` to providers that do not support it.
- Documentation mismatches in runtime behavior and model guidance files.

## [1.0.0] - 2026-02-17

### Added
- Structured runtime contracts in `src/agentforge/contracts.py`
- Tool schema normalization in `src/agentforge/schema_normalizer.py`
- Tool-call ID sanitization/remap in `src/agentforge/tool_id.py`
- Session repair module in `src/agentforge/session_repair.py`
- Mutation classifier in `src/agentforge/tool_mutation.py`
- Session schema versioning + migration to v2
- Dual provider CLI mode (`local` / `openai_compatible`)
- New v1.0 test suite (`src/tests`) and project `pytest.ini`

### Changed
- `LLMInference.chat_completion(...)` now returns `ChatCompletionResult`
- LLM transport now sends/reads structured tool-calling payloads
- Agent loop is structured-first with compatibility fallback parser
- Prompt builder now emits structured API messages
- Tool registry exports OpenAI-compatible tool definitions

### Removed
- Runtime dependency on XML tool-definition injection (`to_xml`)
- Legacy prompt/runtime dead paths tied to ChatML/XML assumptions
