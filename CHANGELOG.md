# Changelog

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
