# Migration Guide: 0.3.x -> 1.0.0

## Overview

v1.0.0 introduces a structured tool-calling runtime and session schema migration.
This release includes breaking internal architecture changes while keeping the main CLI usage and local default flow.

## What Changed

1. `LLMInference.chat_completion(...)` now returns `ChatCompletionResult` instead of plain string.
2. Tool definitions use OpenAI-compatible `tools` schema (`ToolRegistry.to_openai_tools()`).
3. Agent loop consumes structured `assistant.tool_calls` first.
4. Text parser path is now compatibility fallback only.
5. Session format now uses `schema_version=2` with migration/repair on load.

## Session Migration

- Old sessions (0.3.x) are migrated automatically when loaded.
- Migration includes transcript repair:
  - normalizing assistant tool-call blocks
  - pairing tool results with `tool_call_id` when inferable
  - inserting synthetic tool results for missing pairs

No manual migration command is required for standard usage.

## CLI Compatibility

Default local flow remains:

```powershell
python -m agentforge.cli run <model.gguf> --server-exe <llama-server.exe>
```

New remote mode:

```powershell
python -m agentforge.cli run --provider openai_compatible --base-url <url> --model-id <id>
```

## Deprecated/Removed Runtime Paths

- XML tool-definition injection (`to_xml`) is removed from runtime flow.
- Legacy ChatML runtime path has been removed from prompt assembly.

## Validation Checklist After Upgrade

1. Start local mode with `run.bat` and verify normal chat works.
2. Verify tool call execution still works for your model.
3. Open an existing session and confirm it loads without data loss.
4. Run tests:
   ```powershell
   pytest
   ```
