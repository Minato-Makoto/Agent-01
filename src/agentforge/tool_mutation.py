"""
Heuristics to classify mutating vs read-only tool actions.
"""

from typing import Any, Dict, Optional


MUTATING_TOOL_NAMES = {
    "write_file",
    "shell_command",
    "message",
    "ps_export_png",
    "ps_export_jpg",
    "ps_save_document",
}

READ_ONLY_TOOL_NAMES = {
    "read_file",
    "list_directory",
    "search_files",
    "file_info",
    "calculate",
    "web_search",
    "web_scrape",
    "http_request",
    "process_list",
    "browser_get_content",
}

READ_ONLY_ACTIONS = {
    "read",
    "list",
    "search",
    "status",
    "show",
    "fetch",
    "query",
}

PROCESS_MUTATING_ACTIONS = {"write", "send_keys", "submit", "paste", "kill"}
MESSAGE_MUTATING_ACTIONS = {"send", "reply", "edit", "delete", "react", "pin", "unpin"}


def _normalize_action(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    action = value.strip().lower().replace("-", "_").replace(" ", "_")
    return action or None


def is_mutating_tool_call(tool_name: str, args: Dict[str, Any]) -> bool:
    """
    Return True when a tool call likely mutates system/user state.
    """
    normalized = (tool_name or "").strip().lower()
    if not normalized:
        return False
    if normalized in READ_ONLY_TOOL_NAMES:
        return False
    if normalized in MUTATING_TOOL_NAMES:
        return True

    action = _normalize_action(args.get("action")) if isinstance(args, dict) else None
    if normalized == "process":
        return action in PROCESS_MUTATING_ACTIONS
    if normalized == "message":
        return action in MESSAGE_MUTATING_ACTIONS or bool(args.get("content") or args.get("message"))

    if normalized.endswith("_actions"):
        return action is None or action not in READ_ONLY_ACTIONS

    if normalized.startswith("ps_"):
        # Most Photoshop tools are mutating by default.
        readonly_ps = {"ps_get_document_info", "ps_get_active_layer"}
        return normalized not in readonly_ps

    return False
