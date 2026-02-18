# Model Compatibility Guide (v1.0.1)

This document defines runtime compatibility behavior across local and remote providers.

## Compatibility goals

1. Prefer structured tool-calling when endpoint supports it.
2. Degrade gracefully when optional fields are rejected.
3. Keep agent usable in text-only fallback mode when `tools` are unsupported.
4. Preserve transcript consistency under mixed provider quirks.

## Hard requirements

1. Endpoint exposes chat-completions semantics (`/v1/chat/completions` or equivalent).
2. Model is instruction/chat aligned.
3. For reliable tool execution, model should support function/tool-calling natively.

## Runtime degradation ladder (implemented)

When provider rejects fields, Agent-01 retries with minimal mutation:

1. `tools` + `tool_choice` (+ `parallel_tool_calls`)
2. `parallel_tool_calls`
3. `response_format`
4. token cap fallback:
   - `max_completion_tokens` -> `max_tokens`
   - `max_tokens` -> `max_completion_tokens`
5. `reasoning_effort`
6. `reasoning_format`
7. `stream`
8. `grammar` / `stop`

## OpenAI alignment notes

From current OpenAI docs and API reference:

1. Responses API is recommended for new projects.
2. Chat Completions remains supported for `messages`-based flows.
3. `max_tokens` is deprecated in favor of `max_completion_tokens` and is not compatible with `o-series` models.
4. Function calling strictness defaults differ between Chat Completions and Responses.

Agent-01 keeps Chat Completions transport for interoperability, and implements `o-series` token-cap routing with compatibility fallback.

## Provider setup patterns

### Local (llama-server)

1. `PROVIDER=local`
2. Set `SERVER_EXE` and `MODEL_PATH`
3. Keep `MODEL_ID` as label expected by endpoint

### Remote (OpenAI-compatible)

1. `PROVIDER=openai_compatible`
2. Set `BASE_URL`, `MODEL_ID`, `API_KEY_ENV`
3. If `BASE_URL` is OpenAI (`api.openai.com`), API key env must be present

## Validation checklist

1. Run `pytest -q`.
2. Validate at least one structured tool-call turn.
3. Validate at least one fallback case (`tools` rejected).
4. Validate token-cap fallback path (`max_completion_tokens` rejected).
5. Confirm session save/load with tool-call pairing preserved.

## Primary sources

1. https://platform.openai.com/docs/guides/migrate-to-responses
2. https://platform.openai.com/docs/guides/function-calling
3. https://platform.openai.com/docs/guides/structured-outputs
4. https://platform.openai.com/docs/guides/production-best-practices
5. https://api.openai.com/v1/chat/completions (OpenAPI summary via MCP)
6. https://api.openai.com/v1/responses (OpenAPI summary via MCP)

## Additional interoperability references

1. https://docs.vllm.ai/en/latest/features/tool_calling.html
2. https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
3. https://docs.ollama.com/capabilities/tool-calling
4. https://github.com/ggml-org/llama.cpp/releases/tag/b4599

## OpenClaw conceptual references

1. https://docs.openclaw.ai/concepts/model-providers
2. https://docs.openclaw.ai/concepts/model-failover
