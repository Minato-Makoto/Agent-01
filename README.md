# Agent-01

Local-first AI agent with skill-gated tools and a premium terminal UX.

Current runtime path is Chat Completions compatible (`/v1/chat/completions`) with structured tool-calling first and compatibility fallback for mixed OpenAI-compatible providers.

## Production-ready scope

- Structured tool-calling loop (`tools`, `tool_choice`, `tool_calls`, `tool_call_id`)
- Provider-aware transcript policy and tool schema normalization
- Capability fallback for rejected optional parameters
- Remote-mode OpenAI API key preflight when target is `api.openai.com`
- Reasoning parameter split:
  - `reasoning_effort` for OpenAI-style providers
  - `reasoning_format` for local/third-party providers that expose it
- Token cap routing for OpenAI `o-series` models:
  - use `max_completion_tokens`
  - fallback to `max_tokens` automatically if endpoint rejects it
- ASCII-first terminal UI with upgraded box-drawing and Rich coloring (plain-text fallback included)

## Quick start

### Local mode

1. Edit `run.bat` and set `PROVIDER=local`.
2. Set `SERVER_EXE` and `MODEL_PATH` to your llama-server and GGUF model file.
3. Run `run.bat`.

### Remote mode

1. Edit `run.bat` and set `PROVIDER=openai_compatible`.
2. Set `BASE_URL`, `MODEL_ID`, and `API_KEY_ENV`.
3. If `BASE_URL=https://api.openai.com/v1`, ensure `API_KEY_ENV` is set in environment.
4. Run `run.bat`.

Manual CLI example:

```powershell
python -m agentforge.cli run `
  --provider openai_compatible `
  --base-url https://api.openai.com/v1 `
  --model-id gpt-5-mini `
  --api-key-env OPENAI_API_KEY `
  --workspace .\workspace
```

## Runtime overview

```text
User input
  -> Agent core
  -> Chat Completions request (messages + optional tools)
  -> assistant tool calls (if any)
  -> local tool execution
  -> tool result messages
  -> final assistant response
```

Fallback parser (`<tool_call>...</tool_call>`) is only used when structured tool-calling is unavailable or known-bad textual tool payloads are detected.

## Key files

- `src/agentforge/llm_inference.py`: transport, probing, compatibility fallback
- `src/agentforge/agent_core.py`: think-act loop orchestration
- `src/agentforge/transcript_policy.py`: provider transcript sanitization
- `src/agentforge/schema_normalizer.py`: provider-aware schema cleanup
- `src/agentforge/session.py`: session migration and persistence
- `src/agentforge/ui.py`: Rich-powered terminal renderer

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Model Compatibility](docs/MODEL_COMPATIBILITY.md)
- [Runtime Parameters](docs/RUNTIME_PARAMETERS.md)
- [Migration Guide](docs/MIGRATION.md)
- [Changelog](CHANGELOG.md)
