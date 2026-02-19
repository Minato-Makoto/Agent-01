# BLUEPRINT — Agent-01 (AgentForge Runtime)

> Version: **1.0.1** · Python 3.10+ · Windows-first · Single launcher: `run.bat`

---

## 1) Project Overview

Agent-01 is a Windows-first AI agent runtime supporting structured tool-calling over Chat Completions-compatible endpoints. Core design principles:

- **Windows-first**: all entry points and scripts target Windows.
- **Single launcher**: `run.bat` is the only user entry point.
- **Provider-agnostic**: runs with a local llama-server (GGUF) or a remote OpenAI-compatible endpoint.
- **Skill-gated tools**: tools are locked behind a skill system; they are only activated when the agent reads a `SKILL_*.md` file.
- **3-tier context compression**: automatic context window management via soft-trim, graceful summarization, and emergency compression.

---

## 2) Directory Structure

```
Agent-01/
├── run.bat                     # Single launcher (Windows)
├── pyproject.toml              # Package metadata + tool config
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test config (alias of pyproject)
├── .env.example                # Env variable template
├── .gitignore                  # Ignore rules
├── README.md                   # Quick start
├── CHANGELOG.md                # Version history
├── docs/
│   ├── BLUEPRINT_EN.md         # (this file) Full architecture docs
│   ├── BLUEPRINT_VI.md         # Vietnamese version
│   └── TUTORIAL.md             # How to run & parameter reference
├── src/
│   ├── agentforge/             # Core runtime (20 files)
│   ├── builtin_tools/          # Tool implementations (9 modules)
│   └── tests/                  # Test suite (24 test files + conftest)
├── workspace/                  # Runtime data directory
│   ├── IDENTITY.md             # Agent identity (injected into system prompt)
│   ├── SOUL.md                 # Agent personality/values
│   ├── AGENT.md                # Agent instructions & tool contract
│   ├── USER.md                 # User preferences
│   ├── skills/                 # Skill definition folders (8 skills)
│   ├── sessions/               # Session JSON files
│   └── screenshots/            # Browser screenshots
├── adb-mcp/                    # Optional: Photoshop/ADB integration
└── llama-b8069-bin-win-cuda-*/ # Local llama-server binary (gitignored)
```

---

## 3) Runtime Architecture

### 3.1 Main Loop (Tool-calling loop)

```
User Input
    ↓
┌─────────────────────────────────────────────┐
│  Agent.run(user_input)                      │
│  ┌─────────────────────────────────┐        │
│  │ 1. Build system prompt           │       │
│  │    (ContextBuilder: runtime      │       │
│  │     header + bootstrap .md +     │       │
│  │     skills XML)                  │       │
│  │ 2. Build messages                │       │
│  │    (PromptBuilder → OpenAI msg)  │       │
│  │ 3. Call LLM                      │       │
│  │    (LLMInference.chat_completion)│       │
│  │ 4. Parse response                │       │
│  │    - Structured tool_calls? →    │       │
│  │      execute via ToolLoop        │       │
│  │    - Fallback text parse? →      │       │
│  │      ToolCallParser (JSON+XML)   │       │
│  │    - Pure text? → return         │       │
│  │ 5. Append tool results           │       │
│  │ 6. Loop until text-only response │       │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
    ↓
Final Assistant Text → UI Output
```

### 3.2 Detailed Data Flow

1. `cli.py` is a compatibility facade; parser/config lives in `cli_args.py` and runtime wiring lives in `cli_runtime.py`.
2. `run_interactive()` runs the REPL loop: read input → `Agent.run()` → display result.
3. `Agent.run()`:
   - Calls `_update_system_prompt()` (ContextBuilder assembles from workspace .md, skills XML, tools list).
   - Calls `_build_messages()` (PromptBuilder emits OpenAI-format messages).
   - Calls `_run_model_once()` → `LLMInference.chat_completion()`.
   - If tool calls present → `_execute_tool_calls()` → `ToolLoop.execute_tool()` → append results → loop.
   - If model returns text → return result.
4. Session auto-saves after each turn.

---

## 4) Module Map — `src/agentforge/`

| File | Lines | Role |
|------|-------|------|
| `__init__.py` | 7 | Package metadata (`__version__ = "1.0.1"`) |
| `cli.py` | 45 | Compatibility facade entry point (`main`, `run_interactive`) |
| `cli_args.py` | 175 | Parser + env/config loading + `InferenceConfig` mapping |
| `cli_runtime.py` | 268 | REPL loop, component wiring, backend connect flow |
| `agent_core.py` | 439 | `Agent` class: orchestration loop, tool execution, skill activation |
| `llm_inference.py` | 799 | `LLMInference` class: local/remote transport, streaming, compat fallback |
| `contracts.py` | 102 | Shared dataclasses: `ToolCall`, `AssistantMessage`, `ToolMessage`, `ChatCompletionResult`, `ProviderCapabilities` |
| `prompting.py` | 122 | `PromptBuilder`: structured message builder for chat-completions API |
| `tools.py` | 200 | `Tool`, `ToolResult`, `ToolRegistry`: tool definition + OpenAI-compatible schema export |
| `tool_loop.py` | 209 | `ToolLoop`: anti-loop guards (repeat, no-progress, ping-pong, global circuit breaker) |
| `tool_call_parser.py` | 196 | `ToolCallParser`: dual-format parser (JSON + XML) for fallback |
| `tool_id.py` | 59 | `sanitize_tool_call_id`, `remap_tool_call_ids`: ID normalization for strict providers |
| `tool_mutation.py` | 82 | Heuristic classifier for mutating vs read-only tool calls |
| `session.py` | 346 | `SessionManager`: persistent conversation state, schema v2, migration |
| `session_repair.py` | 132 | Transcript repair: normalize tool_calls, pair tool results, insert synthetic results |
| `schema_normalizer.py` | 352 | JSON Schema normalization for provider compatibility (Gemini, Anthropic, OpenAI) |
| `transcript_policy.py` | 251 | Provider-aware transcript sanitization, tool-call-id normalization, pairing repair |
| `skills.py` | 205 | `SkillLoader`: 3-tier skill discovery (workspace > user_config > builtin), activation/deactivation |
| `context.py` | 139 | `ContextBuilder`: dynamic system prompt assembly from workspace .md + runtime state |
| `summarizer.py` | 173 | `Summarizer`: 3-tier context compression (soft-trim → graceful → emergency) |
| `ui.py` | 410 | `ChatUI`: terminal UI, Markdown-rendered assistant output (Rich mode), thinking/reasoning display, tool blocks |

---

## 5) Module Map — `src/builtin_tools/` (8 modules)

| File | Lines | Skill Name | Tools |
|------|-------|------------|-------|
| `file_ops.py` | 166 | File Operations | `write_file`, `list_directory`, `search_files`, `file_info` |
| `sys_ops.py` | 372 | System | `shell_command`, `process_list` |
| `web_ops.py` | 210 | Web Operations | `http_request`, `web_scrape` |
| `web_search.py` | 139 | WebSearch | `web_search` (DuckDuckGo HTML scraping) |
| `browser_tools.py` | 246 | Browser | `browser_navigate`, `browser_click`, `browser_type`, `browser_screenshot`, `browser_get_content`, `browser_evaluate`, `browser_wait`, `browser_scroll`, `browser_select`, `browser_close` |
| `calculator.py` | 134 | Math | `calculate` (safe AST eval) |
| `message_tool.py` | 41 | Communication | `message` |
| `photoshop_tools.py` | 175 | Photoshop | 53 tools via Socket.IO → adb-mcp proxy → UXP Plugin |

### Bootstrap Tools (hardcoded in `agent_core.py`)

- `read_file` — Read any file; also used to activate skills.
- `think` — Transparent reasoning note; the thought content is shown to the user.

Note: UI `thinking` stream comes from model `reasoning_content` tokens and is separate from the `think` tool.

---

## 6) Skill System (MMORPG-style)

### 6.1 Mechanism

1. On startup, the agent has only 2 bootstrap tools: `read_file` and `think`.
2. `SkillLoader` scans `workspace/skills/` for folders containing `SKILL_*.md`.
3. The system prompt includes XML `<available_skills>` listing skills and their status.
4. When the agent wants to use a skill's tools → calls `read_file` on `SKILL_*.md` → `agent_core` detects this and auto-activates the skill, registering tools into `ToolRegistry`.
5. Inactive skills **do not list tool names** in the system prompt (prevents the agent from calling unactivated tools).

### 6.2 3-Tier Priority

```
workspace/skills/  (highest — user overrides)
user_config_dir/   (middle  — user defaults)
builtin_dir/       (lowest  — shipped defaults)
```

### 6.3 Skill File Format

```yaml
---
name: Browser
description: Control headless or visible browser via Playwright.
module: builtin_tools.browser_tools
tools:
  - browser_navigate
  - browser_click
  - browser_type
  # ...
---
# Detailed instructions for the LLM when the skill is activated
```

### 6.4 Current Skills (8 skills)

| Skill Folder | Skill Name | Module |
|-------------|-----------|--------|
| `browser/` | Browser | `builtin_tools.browser_tools` |
| `file_operations/` | File Operations | `builtin_tools.file_ops` |
| `system/` | System | `builtin_tools.sys_ops` |
| `web_operations/` | Web Operations | `builtin_tools.web_ops` |
| `web_search/` | WebSearch | `builtin_tools.web_search` |
| `math/` | Math | `builtin_tools.calculator` |
| `communication/` | Communication | `builtin_tools.message_tool` |
| `photoshop/` | Photoshop | `builtin_tools.photoshop_tools` |

---

## 7) Provider Strategy and Compatibility

### 7.1 Two Modes

| Mode | Trigger | Backend |
|------|---------|---------|
| `local` | `PROVIDER=local` | Agent auto-starts `llama-server.exe` with a GGUF model |
| `openai_compatible` | `PROVIDER=openai_compatible` | Connects to an existing remote endpoint |

### 7.2 Core Request Contract

Payload sent to `/v1/chat/completions`:

- `model` — model identifier
- `messages` — conversation history (OpenAI message format)
- `temperature`, `top_p` — sampling parameters
- Token cap:
  - `max_completion_tokens` for OpenAI `o-series`
  - `max_tokens` for other models/providers
- Optional: `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`
- Optional reasoning control:
  - `reasoning_effort` (OpenAI-style: `low`, `medium`, `high`)
  - `reasoning_format` (local/third-party: `parsed`, `auto`, `none`)

### 7.3 Fallback Ladder (controlled degradation)

When a provider rejects a field, `LLMInference._apply_compat_payload_fallback()` retries by stripping fields in order:

1. `tools` + `tool_choice` (+ `parallel_tool_calls`)
2. `parallel_tool_calls`
3. `response_format`
4. Token cap fallback (`max_completion_tokens` ↔ `max_tokens`)
5. `reasoning_effort`
6. `reasoning_format`
7. `stream`
8. `grammar`
9. `stop`

Max retries: `COMPAT_RETRY_LIMIT` (default 8).

### 7.4 Provider Detection and Transcript Policy

`transcript_policy.py` auto-detects provider kind from base_url:

| Provider | Behavior |
|----------|----------|
| `openai` | Sanitize tool-call IDs, repair pairing |
| `anthropic` | Drop orphan tool results |
| `google` | Strict tool-call ID mode |
| `local` | Minimal sanitization |
| `other` | Generic policy |

---

## 8) Session and Persistence

### 8.1 Session Schema

- **Schema version**: `2`
- **Location**: `workspace/sessions/{session_id}.json`
- **Auto-migration**: legacy transcripts are migrated to v2 on load.
- **Repair**: `session_repair.py` normalizes tool_call blocks, pairs tool results, and inserts synthetic results for orphan tool calls.

### 8.2 Persistence Flow

```
User turn → Agent.run() → SessionManager.add_message()
                        → _save() (atomic write: .tmp → rename)
Tool call  → add_assistant_tool_calls() + add_tool_result()
             → _flush_pending_tool_results() (ensure pairing)
             → _save()
```

### 8.3 Persistence Scope

- Persistent conversation state is stored in `workspace/sessions/*.json`.
- No long-term memory subsystem is loaded in runtime.

---

## 9) System Prompt Assembly

`ContextBuilder.build_system_prompt()` concatenates sections in order:

1. **Runtime header** (programmatic): Agent version, time, OS, workspace path.
2. **Available Tools** (dynamic): from `ToolRegistry`.
3. **Skills XML** (dynamic): from `SkillLoader.build_skills_xml()`.
4. **Bootstrap files** (static): read from workspace — `IDENTITY.md`, `SOUL.md`, `AGENT.md`, `USER.md`.

Sections are joined by `\n\n---\n\n`.

---

## 10) Context Window Management (Summarizer)

3-tier compression pattern (PicoClaw + OpenClaw):

| Tier | Trigger | Action |
|------|---------|--------|
| 0.5 Soft-trim | 60% capacity | Prune long tool results (keep head/tail 500 chars, cut middle) |
| 1 Graceful | 70% capacity | LLM-based summary (preferred) or text concatenation (fallback) |
| 2 Emergency | Context overflow error | Keep 2 most recent messages, drop everything else |

Thresholds are computed as `max_tokens × chars_per_token` (default 4).

---

## 11) Tool Loop Safety (ToolLoop)

| Guard | Threshold | Action |
|-------|-----------|--------|
| Generic repeat | `max_repeats` (default 3) | Block tool call with duplicate args |
| No-progress streak | `global_threshold` (default 30) | Circuit breaker when results are identical |
| Ping-pong | `warning_threshold` (default 10) | Detect A→B→A→B pattern |
| Iteration limit | `max_iterations` (default 10) | Stop loop |
| Timeout | `timeout` (default 60s) | Stop loop |

---

## 12) Security Model

### 12.1 Shell Commands (`sys_ops.py`)

- **Allowlist-default**: only commands in the `ALLOWED_COMMANDS` set are permitted.
- **Blocklist precedence**: `BLOCKED_COMMANDS` (rm, del, format, shutdown, etc.) override the allowlist.
- **Pipeline parsing**: `_split_command_segments()` parses `|`, `||`, `&&`, `;` and validates each segment.
- **Python hardening**: `python/py` inline execution (`-c`, `-m`, stdin script, interactive flags) is blocked.
- **Pip hardening**: destructive subcommands (`install`, `uninstall`, etc.) are blocked; only safe read-style subcommands are allowed.
- **Workspace sandbox by default**: `shell_command` defaults to workspace-only cwd (`SHELL_WORKSPACE_ONLY=1`), with explicit opt-out via `SHELL_WORKSPACE_ONLY=0`.
- **Output limits**: stdout 5000 chars, stderr 2000 chars.

### 12.5 File writes (`file_ops.py`)

- `write_file` is sandboxed to workspace (`AGENTFORGE_WORKSPACE`).
- Relative paths are resolved under workspace.
- Absolute paths outside workspace are rejected with `SECURITY[WRITE_OUTSIDE_WORKSPACE]`.

### 12.6 LLM request rate limiting (`llm_inference.py`)

- Transport enforces `max_requests_per_minute` (default `60`).
- Applies to both regular POST and streaming requests.
- Overflow returns a controlled runtime error instead of unlimited request loops.

### 12.2 Web Requests (`web_ops.py`)

- **SSRF protection**: blocks localhost, private IPs, link-local, multicast.
- **DNS resolution check**: resolves hostnames and blocks if target is a private IP.
- **Scheme restriction**: only `http` and `https`.
- **Control char sanitization**: strips non-printable characters from responses.

### 12.3 API Keys

- **No committed secrets**: `.env` is gitignored; only `.env.example` is tracked.
- **Indirect key access**: API keys are read via env name (`API_KEY_ENV`); runtime resolves `os.environ[key_env_name]`.

### 12.4 Calculator (`calculator.py`)

- **AST-based safe eval**: parses expressions with `ast.parse(mode="eval")`; only allows numeric literals, safe functions (sqrt, sin, cos, etc.), and safe operators.

---

## 13) Streaming and UI

### 13.1 Terminal UI (`ui.py`)

- **Hacker/ASCII 2026 aesthetic**: output prefixed with brackets `[*]`, `[!]`, `[>]`, etc.
- **ANSI streaming**: direct character-by-character writes to stdout.
- **Thinking/reasoning**: dim+italic ANSI escapes for reasoning text.
- **Rich optional**: falls back to plain text if the Rich library is unavailable.
- **Phase machine**: `idle → started → reasoning|assistant → idle`.

### 13.2 Callback System

`StreamCallbacks` dataclass in `agent_core.py`:

| Callback | Purpose |
|----------|---------|
| `on_token` | Token output from assistant |
| `on_reasoning` | Reasoning/thinking token |
| `on_tool_call` | Tool invoked (name, args) |
| `on_tool_result` | Result returned from tool |
| `on_stream_end` | Stream ended |
| `on_thinking_start/end` | Thinking phase start/end |
| `on_skill_activated` | Skill activated |

---

## 14) Configuration and Parameters

### 14.1 Priority Order

User sets ENV variables before calling `run.bat`. The launcher maps them to CLI args:

```
ENV variables (set by user)
  ↓
run.bat defaults (if not defined → set default)
  ↓
run.bat passes both as CLI args to CLI entrypoint
  ↓
cli_args.py resolves final values
```

Bypass: calling `python -m agentforge.cli --flag value` directly overrides everything.

### 14.2 Main Parameters

| Parameter | CLI Flag | Default | Description |
|-----------|----------|---------|-------------|
| `PROVIDER` | `--provider` | `local` | `local` / `openai_compatible` |
| `SERVER_EXE` | `--server-exe` | (in run.bat) | Path to llama-server.exe |
| `MODEL_PATH` | positional | (in run.bat) | Path to .gguf model |
| `BASE_URL` | `--base-url` | `http://127.0.0.1:8080` | Remote endpoint |
| `MODEL_ID` | `--model-id` | `local` | Model identifier |
| `API_KEY_ENV` | `--api-key-env` | `OPENAI_API_KEY` | Env var name holding the key |
| `CTX_SIZE` | `--ctx-size` | `16384` | Context window size |
| `GPU_LAYERS` | `--gpu-layers` | `-1` | GPU layers (`-1` = max) |
| `THREADS` | `--threads` | `0` | CPU threads (`0` = auto) |
| `TEMPERATURE` | `--temp` | `0.1` | Sampling temperature |
| `TOP_P` | `--top-p` | `0.9` | Nucleus sampling |
| `TOP_K` | `--top-k` | `40` | Top-K sampling |
| `REPEAT_PENALTY` | `--repeat-penalty` | `1.1` | Repetition penalty |
| `SEED` | `--seed` | `-1` | Random seed |
| `REASONING_FORMAT` | `--reasoning-format` | `auto` | Local reasoning format |
| `REASONING_EFFORT` | `--reasoning-effort` | `low` | OpenAI reasoning effort |
| `MAX_TOKENS` | `--max-tokens` | `8192` | Max output tokens |
| `HOST` | `--host` | `127.0.0.1` | Backend bind address |
| `PORT` | `--port` | `8080` | Backend port |
| `BOOT_TIMEOUT` | `--boot-timeout` | `120` | Server boot timeout (s) |
| `HEALTH_TIMEOUT` | `--health-timeout` | `2` | Health check timeout (s) |
| `REQUEST_TIMEOUT` | `--request-timeout` | `300` | Request timeout (s) |
| `SHUTDOWN_TIMEOUT` | `--shutdown-timeout` | `5` | Local process shutdown timeout (s) |
| `COMPAT_RETRY_LIMIT` | `--compat-retry-limit` | `8` | Compatibility retry limit |
| `MAX_REQUESTS_PER_MINUTE` | `--max-requests-per-minute` | `60` | LLM requests per minute hard cap |
| `MAX_ITERATIONS` | `--max-iterations` | `10` | Agent loop limit per user turn |
| `MAX_REPEATS` | `--max-repeats` | `3` | Duplicate tool-call repeat guard |
| `AGENT_TIMEOUT` | `--agent-timeout` | `300` | Agent loop timeout (s) |
| `WORKSPACE` | `--workspace` | `./workspace` | Runtime data dir |
| `AGENTFORGE_BROWSER_HEADLESS` | env only | `0` | `0`=visible, `1`=headless |
| `TOOL_TIMEOUT_BROWSER_NAV_MS` | env only | `30000` | `browser_navigate` timeout (ms) |
| `TOOL_TIMEOUT_BROWSER_ACTION_MS` | env only | `5000` | click/type/select/get_content timeout (ms) |
| `TOOL_TIMEOUT_BROWSER_WAIT_MS` | env only | `10000` | `browser_wait` timeout (ms) |
| `TOOL_TIMEOUT_WEB_REQUEST_S` | env only | `30` | `http_request`/`web_scrape` timeout (s) |
| `TOOL_TIMEOUT_WEB_SEARCH_S` | env only | `15` | `web_search` timeout (s) |
| `TOOL_TIMEOUT_PHOTOSHOP_S` | env only | `30` | Photoshop tool timeout (s) |
| `TOOL_TIMEOUT_PROCESS_LIST_S` | env only | `10` | `process_list` timeout (s) |
| `SHELL_WORKSPACE_ONLY` | env only | `1` | `1` enforces workspace-only cwd, `0` disables cwd sandbox |

---

## 15) Test Suite

### 15.1 Configuration

```ini
# pytest.ini / pyproject.toml
testpaths = src/tests
pythonpath = src
addopts = -q
```

### 15.2 Test Files (30 files)

| File | Scope |
|------|-------|
| `conftest.py` | Shared fixtures |
| `test_agent_fallback_parser_activation.py` | Fallback parser triggers |
| `test_calculator_safety.py` | Calculator safe eval |
| `test_cli_config_merge.py` | CLI arg merge logic |
| `test_cli_env_file.py` | .env file loading |
| `test_context_builder.py` | ContextBuilder bootstrap/runtime assembly + load error handling |
| `test_contracts_and_registry.py` | ToolCall, ToolRegistry contracts |
| `test_docs_link_integrity.py` | Doc link validity |
| `test_file_ops_security.py` | Workspace sandbox enforcement for `write_file` |
| `test_integration_mock_provider.py` | Full integration with mock LLM |
| `test_llm_fallback.py` | LLM compatibility fallback |
| `test_llm_rate_limit.py` | LLM request-per-minute guard |
| `test_prompting_builder.py` | PromptBuilder structured message construction/truncation |
| `test_regression_callbacks_streaming.py` | Streaming callback regression |
| `test_schema_provider_compat.py` | Schema normalization per provider |
| `test_security_tools.py` | Shell/web security |
| `test_tool_timeout_env_mapping.py` | Env timeout mapping for browser/web/photoshop/sys tools |
| `test_session_append_guard.py` | Session append guards |
| `test_session_migration.py` | Session schema migration |
| `test_session_repair_helpers.py` | Session repair utilities |
| `test_skill_activation.py` | Skill activation flow |
| `test_smoke_modes.py` | Smoke tests local/remote modes |
| `test_summarizer_resilience.py` | Summarizer edge cases |
| `test_tool_call_parser_fallback.py` | Tool call parser |
| `test_tool_loop_safety.py` | Tool loop guards |
| `test_tool_mutation_policy.py` | Mutation classification |
| `test_tool_async_execution.py` | Async tool execution in sync runtime |
| `test_transcript_policy.py` | Transcript sanitization |
| `test_ui_safety.py` | UI safety |

### 15.3 Quality Gates

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
```

---

## 16) Dependencies

### Runtime

| Package | Role |
|---------|------|
| `rich` | Terminal formatting (optional fallback available) |
| `beautifulsoup4` | Web scraping |
| `playwright` | Browser automation |
| `python-socketio` | Photoshop tools (Socket.IO client) |
| `websocket-client` | WebSocket transport for socketio |
| `pyyaml` | Skill metadata parsing |

### Dev

| Package | Role |
|---------|------|
| `pytest>=8` | Testing |
| `ruff>=0.6` | Linting |

---

## 17) Optional: adb-mcp Integration

- **Directory**: `adb-mcp/` (in-repo, optional).
- **Purpose**: Control Adobe Photoshop via UXP plugin.
- **Architecture**: `Agent → Socket.IO → adb-mcp proxy (Node.js) → UXP Plugin → Photoshop`.
- **Requirements**: Adobe Photoshop 26.0+, UXP Developer Mode, `node adb-mcp/adb-proxy-socket/proxy.js`.
- **adb-mcp is NOT required to run core Agent-01**.

---

## 18) Workspace Bootstrap Files

On startup, `ContextBuilder` reads files from the workspace:

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Name, role, version, operating modes, bootstrap tools |
| `SOUL.md` | Personality, values, communication style |
| `AGENT.md` | Instructions, tool calling contract, safety rules, skill activation flow |
| `USER.md` | User preferences, context |

These files are **static content** — AI models/developers can customize them.

---

## 19) CI Blueprint (proposed)

### Windows CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest ruff
      - run: python -m pytest -q
      - run: python -m compileall -q src
      - run: |
          $env:PYTHONPATH='src'
          python -m agentforge.cli --help
```

---

## 20) Design Patterns and Conventions

### 20.1 Patterns Used

- **OpenAI message contract**: The entire runtime uses OpenAI Chat Completions `messages` format.
- **Structured-first, fallback-second**: Prefers structured `tool_calls`; falls back to ToolCallParser when provider doesn't support it.
- **PicoClaw/OpenClaw patterns**: Many modules reference patterns from PicoClaw (Go) and OpenClaw (TypeScript).
- **Dual-output ToolResult**: `for_llm` (context for LLM) and `for_user` (display for user) separate content.
- **Atomic file I/O**: Session persistence uses atomic writes (write .tmp, then rename).

### 20.2 Coding Conventions

- **Python 3.10+**: uses type hints, dataclasses.
- **Ruff** with `select = ["F"]` (flake8 pyflakes rules only), ignoring `F401, F541, F841`.
- **Line length**: 100 chars.
- **Logging**: `logging.getLogger(__name__)` in every module.
- **Error handling**: graceful fallback, never crash the runtime.

---

## 21) Notes for AI Models/Developers

1. **When changing `run.bat`**, always run launcher smoke (`cmd /c run.bat` with `PROVIDER=openai_compatible` and `EXTRA_ARGS=--help`) before merge.
2. **Each new tool** must have: a definition in `builtin_tools/`, a skill file `SKILL_*.md` in `workspace/skills/`, and a `register()` function.
3. **Test before merging** — all changes should pass `python -m pytest -q`.
4. **Do not hardcode secrets** — use env vars.
5. **New modules in `agentforge/`** must be imported in `cli.py` or `agent_core.py` to wire into the runtime.
6. **Session backward compatibility** — if changing the schema, bump `SESSION_SCHEMA_VERSION` and add migration logic in `migrate_session_payload()`.
7. **Tool schemas** must be valid JSON Schema with `type: "object"` at top-level — `schema_normalizer.py` will normalize, but it's best to write correctly from the start.

---

## 22) References

- PyPA `pyproject.toml`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- pip repeatable installs: https://pip.pypa.io/en/stable/topics/repeatable-installs/
- GitHub Actions Python: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- OpenAI Chat Completions: https://platform.openai.com/docs/api-reference/chat
- OpenAI migrate to Responses: https://platform.openai.com/docs/guides/migrate-to-responses
- OpenClaw concepts:
  - https://docs.openclaw.ai/concepts/model-providers
  - https://docs.openclaw.ai/concepts/model-failover
