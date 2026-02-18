"""
AgentForge — Communication tools.

Tools: message
"""

from typing import Any, Dict

from agentforge.tools import Tool, ToolRegistry, ToolResult


def register(registry: ToolRegistry, skill_name: str = "Communication") -> None:
    """Register communication tools."""
    tools = [
        Tool(
            name="message",
            description="Send a formatted message to the user.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Message content."},
                    "format": {"type": "string", "description": "Format: text, markdown, json.", "default": "markdown"}
                },
                "required": ["content"]
            },
            execute_fn=_message,
        ),
    ]
    registry.register_skill(skill_name, tools)


def _message(args: Dict[str, Any]) -> ToolResult:
    content = args.get("content", "")
    fmt = args.get("format", "markdown")

    if not content:
        return ToolResult.error_result("Missing 'content'")

    for_llm = f"[message/{fmt}] {content}"
    return ToolResult.llm_result(for_llm=for_llm, for_user=content)
