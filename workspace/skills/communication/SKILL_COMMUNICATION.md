---
name: Communication
description: Send explicit user-facing messages from tool execution paths.
module: builtin_tools.message_tool
tools:
  - message
---

# Communication Skill

Provides one utility tool for user-visible notifications.

## `message`

- Required: `content` (string)
- Optional: `format` (`text`, `markdown`, `json`; default `markdown`)
- Behavior:
  - user sees `content`
  - model context records `[message/<format>] <content>`

Use this only when explicit output framing is needed from a tool step.
