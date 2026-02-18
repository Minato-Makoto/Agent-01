# Architecture (v1.0.1)

## Runtime strategy

Agent-01 uses a structured tool-calling loop on top of Chat Completions-compatible endpoints.

1. Build request from current conversation state.
2. Send `messages` plus optional tool definitions.
3. Parse assistant output.
4. Execute tool calls when present.
5. Append `role=tool` results with `tool_call_id`.
6. Repeat until assistant returns final text.

## Why Chat Completions first

1. Broad interoperability with local and third-party OpenAI-compatible servers.
2. Existing loop and transcript model are aligned to `assistant.tool_calls` and `tool_call_id`.
3. Migration path to Responses API remains open per feature/domain.

OpenAI recommends Responses API for new projects, but this codebase intentionally keeps Chat Completions as primary transport for cross-provider compatibility.

## Request contract

Primary fields:

- `model`
- `messages`
- token cap field:
  - `max_completion_tokens` for OpenAI `o-series` model IDs
  - otherwise `max_tokens`
- `temperature`
- `top_p`
- optional `tools`
- optional `tool_choice`
- optional `parallel_tool_calls`
- optional `response_format`
- optional reasoning control:
  - `reasoning_effort` on OpenAI-style providers
  - `reasoning_format` on local/third-party providers

## Capability fallback ladder

When provider rejects fields, runtime retries with minimal payload mutations:

1. `tools` + `tool_choice` (+ `parallel_tool_calls`)
2. `parallel_tool_calls`
3. `response_format`
4. token cap fallback:
  - `max_completion_tokens` -> `max_tokens`
  - `max_tokens` -> `max_completion_tokens`
5. `reasoning_effort`
6. `reasoning_format`
7. `stream`
8. `grammar`
9. `stop`

## Provider-aware behavior

- Transcript policy sanitizes and repairs tool-call/result pairing where needed.
- Tool schemas are normalized per provider family before request send.
- OpenAI API preflight enforces API key env presence for `api.openai.com`.

## Session model

- Schema version: `2`
- Legacy transcripts are migrated and repaired on load.
- Runtime append path preserves assistant tool-call/result pairing.

## UI layer

`src/agentforge/ui.py` is ASCII-first for:

- session header
- status/error blocks
- tool call/result blocks
- streamed answer and reasoning traces

The same format is preserved when `rich` is unavailable.

## Module map

- `contracts.py`: shared dataclasses
- `llm_inference.py`: transport and compatibility handling
- `agent_core.py`: orchestration
- `tool_loop.py`: loop safety guards
- `tools.py`: tool registry and OpenAI-compatible export
- `context.py`: dynamic system prompt assembly from workspace guidance files

## Root layout (standardized)

- `run.bat`: Windows launcher (dev/prod entry)
- `scripts/`: setup/lint/test/build/start wrappers
- `src/agentforge/`: core runtime package
- `src/builtin_tools/`: builtin skill tool modules
- `src/tests/`: regression + compatibility test suite
- `docs/`: architecture, deployment, runbook, migration notes
