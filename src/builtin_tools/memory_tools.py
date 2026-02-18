"""
AgentForge — Memory tools for agent self-learning.

Tools: remember, recall, note
Allows the agent to persist knowledge across sessions via MEMORY.md and daily notes.
Pattern: PicoClaw memory.go
"""

from typing import Any, Dict

from agentforge.tools import Tool, ToolRegistry, ToolResult
from agentforge.memory import MemoryStore

# Module-level storage — set by register() 
_memory_store: MemoryStore = None


def init_memory_store(workspace: str) -> None:
    """Initialize the memory store. Must be called before register()."""
    global _memory_store
    _memory_store = MemoryStore(workspace)


def register(registry: ToolRegistry, skill_name: str = "Memory") -> None:
    """Register memory tools. Call init_memory_store() first."""
    tools = [
        Tool(
            name="remember",
            description="Save important information to long-term memory (MEMORY.md). Use this when you learn something about the user, their preferences, or important facts that should persist across sessions.",
            input_schema={
                "type": "object",
                "properties": {
                    "entry": {
                        "type": "string",
                        "description": "The information to remember (will be appended to MEMORY.md)."
                    },
                },
                "required": ["entry"],
            },
            execute_fn=_remember,
        ),
        Tool(
            name="recall",
            description="Read long-term memory (MEMORY.md) to recall previously saved information.",
            input_schema={
                "type": "object",
                "properties": {},
            },
            execute_fn=_recall,
        ),
        Tool(
            name="note",
            description="Add a timestamped note to today's daily log. Use for tracking daily activities, tasks completed, or observations.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The note content to append to today's log."
                    },
                },
                "required": ["content"],
            },
            execute_fn=_note,
        ),
    ]
    registry.register_skill(skill_name, tools)


def _remember(args: Dict[str, Any]) -> ToolResult:
    entry = args.get("entry", "")
    if not entry:
        return ToolResult.error_result("Missing 'entry'")
    if not _memory_store:
        return ToolResult.error_result("Memory store not initialized")

    # Read existing, append new entry
    existing = _memory_store.read_long_term()
    if existing:
        new_content = existing.rstrip() + "\n\n" + entry
    else:
        new_content = "# Long-term Memory\n\n" + entry

    _memory_store.write_long_term(new_content)
    return ToolResult.silent_result(f"Saved to long-term memory: {entry[:100]}")


def _recall(args: Dict[str, Any]) -> ToolResult:
    if not _memory_store:
        return ToolResult.error_result("Memory store not initialized")

    content = _memory_store.read_long_term()
    if not content or content.strip() == "# Long-term Memory":
        return ToolResult.silent_result("Long-term memory is empty.")
    return ToolResult.silent_result(content)


def _note(args: Dict[str, Any]) -> ToolResult:
    content = args.get("content", "")
    if not content:
        return ToolResult.error_result("Missing 'content'")
    if not _memory_store:
        return ToolResult.error_result("Memory store not initialized")

    _memory_store.append_today(content)
    return ToolResult.silent_result(f"Added to today's daily note: {content[:100]}")
