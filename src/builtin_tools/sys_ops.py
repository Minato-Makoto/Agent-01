"""
AgentForge — System tools.

Tools:
- shell_command
- process_list

Security profile: strict-default allowlist with blocked-command precedence.
"""

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agentforge.tools import Tool, ToolRegistry, ToolResult


def register(registry: ToolRegistry, skill_name: str = "System") -> None:
    tools = [
        Tool(
            name="shell_command",
            description="Execute a shell command. Returns stdout, stderr, and exit code.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute."},
                    "cwd": {"type": "string", "description": "Working directory."},
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (1-120).",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
            execute_fn=_shell_command,
        ),
        Tool(
            name="process_list",
            description="List running processes.",
            input_schema={
                "type": "object",
                "properties": {"filter": {"type": "string", "description": "Name filter."}},
            },
            execute_fn=_process_list,
        ),
    ]
    registry.register_skill(skill_name, tools)


ALLOWED_COMMANDS = {
    "ls",
    "dir",
    "cat",
    "type",
    "head",
    "tail",
    "wc",
    "grep",
    "findstr",
    "find",
    "pwd",
    "mkdir",
    "cp",
    "copy",
    "move",
    "mv",
    "python",
    "py",
    "pip",
    "npm",
    "node",
    "npx",
    "git",
    "echo",
    "set",
    "env",
    "whoami",
    "hostname",
    "date",
    "time",
    "ps",
    "tasklist",
    "lsof",
    "netstat",
    "ping",
    "curl",
    "wget",
    "touch",
    "tree",
    "du",
    "df",
    "file",
    "stat",
    "chmod",
}

BLOCKED_COMMANDS = {
    "rm",
    "del",
    "rmdir",
    "format",
    "mkfs",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "dd",
    "fdisk",
    "parted",
}

STDOUT_LIMIT = 5000
STDERR_LIMIT = 2000

PYTHON_BLOCKED_FLAGS = {"-c", "-m", "-i", "-"}
PIP_ALLOWED_SUBCOMMANDS = {"list", "show", "freeze", "help", "-v", "--version"}


def _workspace_root() -> Path:
    raw = os.environ.get("AGENTFORGE_WORKSPACE", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.cwd() / "workspace").resolve()


def _is_within_workspace(path: Path) -> bool:
    workspace = _workspace_root()
    try:
        path.resolve().relative_to(workspace)
        return True
    except ValueError:
        return False


def _split_command_segments(command: str) -> List[str]:
    """
    Split command string by shell control operators at top-level.

    Handles:
    - `|`, `||`, `&&`, `;`
    - quote contexts
    - subshell and command substitution depth `(...)`, `$(...)`
    """
    if not command:
        return []

    out: List[str] = []
    buf: List[str] = []
    quote: str = ""
    escape = False
    paren_depth = 0
    i = 0

    def flush():
        seg = "".join(buf).strip()
        if seg:
            out.append(seg)
        buf.clear()

    while i < len(command):
        ch = command[i]
        nxt = command[i + 1] if i + 1 < len(command) else ""

        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\" and quote != "'":
            buf.append(ch)
            escape = True
            i += 1
            continue

        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            i += 1
            continue

        if ch in ("'", '"', "`"):
            quote = ch
            buf.append(ch)
            i += 1
            continue

        if ch == "$" and nxt == "(":
            paren_depth += 1
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue

        if ch == "(":
            paren_depth += 1
            buf.append(ch)
            i += 1
            continue

        if ch == ")" and paren_depth > 0:
            paren_depth -= 1
            buf.append(ch)
            i += 1
            continue

        if paren_depth == 0:
            if ch == ";":
                flush()
                i += 1
                continue
            if ch == "|" and nxt == "|":
                flush()
                i += 2
                continue
            if ch == "&" and nxt == "&":
                flush()
                i += 2
                continue
            if ch == "|":
                flush()
                i += 1
                continue

        buf.append(ch)
        i += 1

    flush()
    return out


def _extract_command_name(segment: str) -> str:
    if not segment:
        return ""
    segment = segment.strip()
    if segment.startswith("(") and segment.endswith(")"):
        inner = segment[1:-1].strip()
        nested = _split_command_segments(inner)
        if not nested:
            return ""
        return _extract_command_name(nested[0])
    try:
        tokens = shlex.split(segment, posix=(sys.platform != "win32"))
    except ValueError:
        tokens = segment.split()
    if not tokens:
        return ""
    cmd = os.path.basename(tokens[0]).lower()
    if cmd.endswith(".exe"):
        cmd = cmd[:-4]
    return cmd


def _tokenize_segment(segment: str) -> List[str]:
    try:
        tokens = shlex.split(segment, posix=(sys.platform != "win32"))
    except ValueError:
        tokens = segment.split()
    return tokens


def _validate_python_invocation(tokens: List[str]) -> Tuple[bool, str, str]:
    if len(tokens) <= 1:
        return False, "BLOCKED_PYTHON_INVOCATION", "Interactive python shell is not allowed"

    first_arg = tokens[1].strip()
    first_arg_lower = first_arg.lower()
    if first_arg_lower in PYTHON_BLOCKED_FLAGS or first_arg_lower.startswith("-c"):
        return (
            False,
            "BLOCKED_PYTHON_FLAG",
            f"Python flag '{first_arg}' is blocked. Inline code execution is not allowed.",
        )

    if first_arg_lower in {"-v", "--version", "-h", "--help"}:
        return True, "OK", ""

    if first_arg.startswith("-"):
        return (
            False,
            "BLOCKED_PYTHON_FLAG",
            f"Python flag '{first_arg}' is blocked for shell_command safety.",
        )

    script_path = Path(first_arg).expanduser()
    if not script_path.is_absolute():
        script_path = (Path.cwd() / script_path).resolve()
    else:
        script_path = script_path.resolve()

    if script_path.suffix.lower() != ".py":
        return (
            False,
            "BLOCKED_PYTHON_SCRIPT",
            "Only .py script execution is allowed for python command.",
        )

    if not _is_within_workspace(script_path):
        return (
            False,
            "BLOCKED_PYTHON_PATH",
            f"Python script must be inside workspace: {_workspace_root()}",
        )

    return True, "OK", ""


def _validate_pip_invocation(tokens: List[str]) -> Tuple[bool, str, str]:
    if len(tokens) <= 1:
        return False, "BLOCKED_PIP_SUBCOMMAND", "pip requires an explicit safe subcommand"
    sub = tokens[1].strip().lower()
    if sub not in PIP_ALLOWED_SUBCOMMANDS:
        return (
            False,
            "BLOCKED_PIP_SUBCOMMAND",
            f"pip subcommand '{sub}' is blocked. Allowed: {', '.join(sorted(PIP_ALLOWED_SUBCOMMANDS))}",
        )
    return True, "OK", ""


def _validate_command_policy(command_name: str, tokens: List[str]) -> Tuple[bool, str, str]:
    if command_name in {"python", "py"}:
        return _validate_python_invocation(tokens)
    if command_name == "pip":
        return _validate_pip_invocation(tokens)
    return True, "OK", ""


def _extract_commands(command_string: str) -> List[str]:
    commands: List[str] = []
    for segment in _split_command_segments(command_string):
        name = _extract_command_name(segment)
        if name:
            commands.append(name)
    return commands


def _validate_command(command_string: str) -> Tuple[bool, str, str]:
    """
    Validate against strict allowlist.

    Returns tuple: (allowed, code, reason).
    """
    segments = _split_command_segments(command_string)
    if not segments:
        return False, "PARSE_ERROR", "Could not parse command"

    for segment in segments:
        tokens = _tokenize_segment(segment)
        if not tokens:
            return False, "PARSE_ERROR", "Could not tokenize command segment"

        cmd = os.path.basename(tokens[0]).lower()
        if cmd.endswith(".exe"):
            cmd = cmd[:-4]

        if cmd in BLOCKED_COMMANDS:
            return False, "BLOCKED_COMMAND", f"Command '{cmd}' is blocked for safety"
        if cmd not in ALLOWED_COMMANDS:
            return (
                False,
                "NOT_ALLOWED",
                f"Command '{cmd}' is not in allowed list: {', '.join(sorted(ALLOWED_COMMANDS))}",
            )
        allowed, code, reason = _validate_command_policy(cmd, tokens)
        if not allowed:
            return False, code, reason

    return True, "OK", ""


def _sanitize_timeout(value: Any) -> int:
    try:
        t = int(value)
    except Exception:
        t = 30
    return max(1, min(120, t))


def _shell_command(args: Dict[str, Any]) -> ToolResult:
    command = str(args.get("command", "")).strip()
    cwd = args.get("cwd")
    timeout = _sanitize_timeout(args.get("timeout", 30))

    if not command:
        return ToolResult.error_result("Missing 'command'")

    allowed, code, reason = _validate_command(command)
    if not allowed:
        return ToolResult.error_result(f"SECURITY[{code}]: {reason}")

    if cwd:
        cwd = str(cwd)
        if not os.path.isdir(cwd):
            return ToolResult.error_result(f"SECURITY[INVALID_CWD]: Not a directory: {cwd}")

    try:
        if sys.platform == "win32":
            shell_cmd = ["powershell", "-Command", command]
        else:
            shell_cmd = ["bash", "-c", command]

        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=os.environ.copy(),
        )

        return ToolResult(
            success=True,
            output={
                "stdout": result.stdout[:STDOUT_LIMIT],
                "stderr": result.stderr[:STDERR_LIMIT],
                "exit_code": result.returncode,
                "timed_out": False,
            },
        )
    except subprocess.TimeoutExpired:
        return ToolResult.error_result(f"SECURITY[TIMEOUT]: Command timed out after {timeout}s")
    except Exception as e:
        return ToolResult.error_result(f"RUNTIME[EXEC_ERROR]: {e}")


def _process_list(args: Dict[str, Any]) -> ToolResult:
    name_filter = str(args.get("filter", "")).lower().strip()
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n")
            processes = []
            for line in lines[:50]:
                parts = line.strip().strip('"').split('","')
                if len(parts) < 5:
                    continue
                name = parts[0].strip('"')
                pid = parts[1].strip('"')
                mem = parts[4].strip('"')
                if not name_filter or name_filter in name.lower():
                    processes.append({"name": name, "pid": pid, "memory": mem})
        else:
            result = subprocess.run(
                ["ps", "aux", "--sort=-rss"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n")[1:51]
            processes = []
            for line in lines:
                parts = line.split(None, 10)
                if len(parts) < 11:
                    continue
                name = parts[10]
                if not name_filter or name_filter in name.lower():
                    processes.append(
                        {
                            "name": name,
                            "pid": parts[1],
                            "cpu": parts[2],
                            "memory": parts[3],
                        }
                    )
        return ToolResult(success=True, output=processes)
    except Exception as e:
        return ToolResult.error_result(str(e))
