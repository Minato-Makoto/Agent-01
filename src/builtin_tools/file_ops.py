"""
AgentForge — File Operations tools.

Tools: read_file, write_file, list_directory, search_files, file_info
"""

import os
import json
import glob
from pathlib import Path
from typing import Any, Dict, List

from agentforge.tools import Tool, ToolRegistry, ToolResult


def register(registry: ToolRegistry, skill_name: str = "File Operations") -> None:
    """Register file operation tools (excluding read_file — provided by bootstrap)."""
    tools = [
        Tool(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file."},
                    "content": {"type": "string", "description": "Content to write."}
                },
                "required": ["path", "content"]
            },
            execute_fn=_write_file,
        ),
        Tool(
            name="list_directory",
            description="List files and subdirectories in a directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the directory."},
                    "recursive": {"type": "boolean", "description": "List recursively.", "default": False}
                },
                "required": ["path"]
            },
            execute_fn=_list_directory,
        ),
        Tool(
            name="search_files",
            description="Search for files matching a glob pattern.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to search in."},
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py', '**/*.md')."},
                    "max_results": {"type": "integer", "description": "Max results to return.", "default": 20}
                },
                "required": ["path", "pattern"]
            },
            execute_fn=_search_files,
        ),
        Tool(
            name="file_info",
            description="Get metadata about a file (size, modified date, type).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file."}
                },
                "required": ["path"]
            },
            execute_fn=_file_info,
        ),
    ]
    registry.register_skill(skill_name, tools)


def _read_file(args: Dict[str, Any]) -> ToolResult:
    path = args.get("path", "")
    if not path:
        return ToolResult(success=False, output=None, error="Missing 'path'")
    if not os.path.exists(path):
        return ToolResult(success=False, output=None, error=f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))


def _write_file(args: Dict[str, Any]) -> ToolResult:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return ToolResult(success=False, output=None, error="Missing 'path'")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))


def _list_directory(args: Dict[str, Any]) -> ToolResult:
    path = args.get("path", "")
    recursive = args.get("recursive", False)
    if not path or not os.path.isdir(path):
        return ToolResult(success=False, output=None, error=f"Not a valid directory: {path}")
    try:
        entries = []
        if recursive:
            for root, dirs, files in os.walk(path):
                for name in dirs:
                    full = os.path.join(root, name)
                    entries.append({"name": os.path.relpath(full, path), "type": "directory"})
                for name in files:
                    full = os.path.join(root, name)
                    entries.append({
                        "name": os.path.relpath(full, path),
                        "type": "file",
                        "size": os.path.getsize(full)
                    })
        else:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                entry = {"name": name, "type": "directory" if os.path.isdir(full) else "file"}
                if os.path.isfile(full):
                    entry["size"] = os.path.getsize(full)
                entries.append(entry)
        return ToolResult(success=True, output=entries)
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))


def _search_files(args: Dict[str, Any]) -> ToolResult:
    path = args.get("path", "")
    pattern = args.get("pattern", "")
    max_results = args.get("max_results", 20)
    if not path or not pattern:
        return ToolResult(success=False, output=None, error="Missing 'path' or 'pattern'")
    try:
        search_pattern = os.path.join(path, pattern)
        matches = glob.glob(search_pattern, recursive=True)[:max_results]
        return ToolResult(success=True, output=matches)
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))


def _file_info(args: Dict[str, Any]) -> ToolResult:
    path = args.get("path", "")
    if not path or not os.path.exists(path):
        return ToolResult(success=False, output=None, error=f"Path not found: {path}")
    try:
        stat = os.stat(path)
        import datetime
        info = {
            "path": os.path.abspath(path),
            "name": os.path.basename(path),
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat.st_size,
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
        return ToolResult(success=True, output=info)
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))
