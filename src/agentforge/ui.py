"""
AgentForge terminal chat UI — hacker/ASCII 2026 edition.

Streaming:
- Direct character-by-character writes to stdout (natural terminal wrapping)
- ANSI dim+italic for reasoning/thinking text
- Phase: idle → started → reasoning|assistant → idle
- Headers printed on first token (prevents duplicate headers)
"""

from __future__ import annotations

import json
import shutil
import sys
from typing import Any, Dict, List, Optional

from .__init__ import __version__

try:
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Banner ──────────────────────────────────────────────────────

_BANNER_LINES = [
    "    ___               __      ______",
    "   /   |  ____ ____ _/ /_    / ____/___  _________ ____",
    "  / /| | / __ `/ _ `/ __/   / /_  / __ \\/ ___/ __ `/ _ \\",
    " / ___ |/ /_/ /  __/ /_    / __/ / /_/ / /  / /_/ /  __/",
    "/_/  |_|\\__, /\\___/\\__/   /_/    \\____/_/   \\__, /\\___/",
    "       /____/                               /____/",
]

# ── Constants ───────────────────────────────────────────────────

TERMINAL_MIN_WIDTH = 60
TERMINAL_MAX_WIDTH = 120
TERMINAL_FALLBACK_WIDTH = 100
TOOL_RESULT_LINE_LIMIT = 15

PREFIX_STATUS = "[*]"
PREFIX_ERROR = "[!]"
PREFIX_LOG = "[-]"
PREFIX_ASSISTANT = "[>]"
PREFIX_REASONING = "[~]"
PREFIX_TOOL = "[>>]"
PREFIX_RESULT = "[<<]"

# ANSI escape codes for reasoning styling
_ANSI_DIM_ITALIC = "\033[2;3m"
_ANSI_RESET = "\033[0m"

# ── Theme (dict-based) ─────────────────────────────────────────

THEME_RICH: Dict[str, str] = {
    "rule": "dim",
    "banner": "bold bright_cyan",
    "version": "dim cyan",
    "status": "green",
    "hint": "dim",
    "error": "bold red",
    "log": "dim",
    "assistant_header": "bold bright_cyan",
    "reasoning_header": "dim yellow",
    "tool_title": "bold yellow",
    "tool_body": "dim yellow",
    "result_title": "bold green",
    "result_body": "dim green",
    "goodbye": "dim green",
}

THEME_PLAIN: Dict[str, str] = {k: "" for k in THEME_RICH}


# ── Helpers ─────────────────────────────────────────────────────

def _short(value: Any, limit: int = 80) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _truncate_lines(lines: List[str], limit: int) -> List[str]:
    if len(lines) <= limit:
        return lines
    return lines[:limit] + ["... (truncated)"]


# ── ChatUI ──────────────────────────────────────────────────────

class ChatUI:
    """Terminal chat UI — hacker/ASCII 2026 aesthetic."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._use_rich = bool(
            HAS_RICH
            and getattr(sys.stdout, "isatty", lambda: False)()
            and getattr(sys.stdin, "isatty", lambda: False)()
        )
        self.console = Console(soft_wrap=True) if self._use_rich else None
        self.theme = THEME_RICH if self._use_rich else THEME_PLAIN

        # Stream state
        # idle → started → (reasoning | assistant) → idle
        self._phase = "idle"
        self._at_line_start = False
        self._dim_active = False  # ANSI dim currently applied

        # Spinner
        self._spinner_live: Optional[Any] = None

        # Encoding
        self._encoding = self._detect_encoding()
        self._unicode_ok = self._can_encode("─")

        # Raw output target (bypasses Rich for streaming)
        if self._use_rich and self.console is not None:
            self._raw_target = getattr(self.console, "file", None) or sys.stdout
        else:
            self._raw_target = sys.stdout

    # ── Welcome ─────────────────────────────────────────────

    def welcome(
        self,
        model_name: str,
        tools: Optional[List[str]] = None,
        *,
        session_id: str = "",
        skill_count: int = 0,
        total_tool_count: int = 0,
        workspace: str = "",
        provider: str = "",
    ) -> None:
        self._rule()
        for line in _BANNER_LINES:
            self._emit(line, style=self.theme["banner"])
        self._emit(f"  v{__version__}", style=self.theme["version"])
        self._rule()

        tool_count = len(tools) if tools else 0
        self._prefixed(PREFIX_STATUS, f"model   : {model_name}", self.theme["status"])
        if provider:
            self._prefixed(PREFIX_STATUS, f"runtime : {provider}", self.theme["status"])
        self._prefixed(
            PREFIX_STATUS,
            f"tools   : {tool_count} active | {skill_count} skills ({total_tool_count} total)",
            self.theme["status"],
        )
        if workspace:
            self._prefixed(PREFIX_STATUS, f"workspace: {workspace}", self.theme["hint"])
        if session_id:
            self._prefixed(PREFIX_STATUS, f"session : {session_id}", self.theme["hint"])
        self._prefixed(
            PREFIX_STATUS,
            "commands: exit | reset | clear | skills | memory | session",
            self.theme["hint"],
        )
        self._rule()
        self._emit("")

    # ── Status / Error / Log ────────────────────────────────

    def status(self, msg: str) -> None:
        self._ensure_stream_closed()
        self._prefixed(PREFIX_STATUS, msg, self.theme["hint"] or self.theme["status"])

    def error(self, msg: str) -> None:
        self._ensure_stream_closed()
        self._prefixed(f"{PREFIX_ERROR} ERROR:", msg, self.theme["error"])

    def log(self, msg: str) -> None:
        if not self.verbose:
            return
        self._ensure_stream_closed()
        self._prefixed(PREFIX_LOG, msg, self.theme["log"])

    # ── Input ───────────────────────────────────────────────

    def get_input(self) -> Optional[str]:
        prompt = "❯ " if self._unicode_ok else "> "
        try:
            if self._use_rich and self.console is not None:
                line = self.console.input(f"[bold green]{prompt}[/bold green]")
            else:
                line = input(prompt)
            return line.strip()
        except (EOFError, KeyboardInterrupt):
            return None

    # ── Thinking spinner ────────────────────────────────────

    def thinking_start(self) -> None:
        if not (self._use_rich and self.console is not None):
            return
        if self._spinner_live is not None:
            return
        try:
            spinner = Spinner("dots", text="processing...", style="dim green")
            self._spinner_live = Live(
                spinner,
                console=self.console,
                refresh_per_second=10,
                transient=True,
            )
            self._spinner_live.start()
        except Exception:
            self._spinner_live = None

    def thinking_stop(self) -> None:
        if self._spinner_live is None:
            return
        try:
            self._spinner_live.stop()
        except Exception:
            pass
        self._spinner_live = None

    # ── Streaming ───────────────────────────────────────────
    # Direct writes to stdout. Terminal handles wrapping.
    # ANSI dim+italic for reasoning, reset for assistant.

    def stream_start(self) -> None:
        """Signal streaming is about to begin. Headers deferred to first token."""
        self.thinking_stop()
        if self._phase not in ("idle", "started"):
            self._ensure_stream_closed()
        self._phase = "started"

    def stream_token(self, token: str) -> None:
        """Stream assistant content token."""
        if not token:
            return
        self.thinking_stop()

        if self._phase in ("idle", "started"):
            self._emit("")
            self._prefixed(PREFIX_ASSISTANT, "Agent-01:", self.theme["assistant_header"])
            self._phase = "assistant"
            self._at_line_start = True

        elif self._phase == "reasoning":
            # TRANSITION: reasoning → assistant
            self._end_dim()
            self._raw_write("\n\n")
            self._prefixed(PREFIX_ASSISTANT, "Agent-01:", self.theme["assistant_header"])
            self._phase = "assistant"
            self._at_line_start = True

        self._raw_write(token)

    def stream_reasoning(self, token: str) -> None:
        """Stream reasoning/thinking token (dim italic)."""
        if not token:
            return
        self.thinking_stop()

        if self._phase in ("idle", "started", "assistant"):
            if self._phase == "assistant":
                self._end_dim()
                self._raw_write("\n\n")
            elif self._phase == "started":
                self._emit("")
            self._prefixed(PREFIX_REASONING, "thinking:", self.theme["reasoning_header"])
            self._phase = "reasoning"
            self._at_line_start = True
            self._start_dim()

        self._raw_write(token)

    def stream_end(self) -> None:
        """End current stream phase."""
        self.thinking_stop()
        self._ensure_stream_closed()

    # ── Tool display ────────────────────────────────────────

    def show_tool_call(self, name: str, arguments: Dict[str, Any]) -> None:
        self.thinking_stop()
        self._ensure_stream_closed()
        self._emit("")
        if not arguments:
            self._prefixed(PREFIX_TOOL, f"TOOL: {name}()", self.theme["tool_title"])
        else:
            args_str = _short(arguments, 72)
            self._prefixed(PREFIX_TOOL, f"TOOL: {name}", self.theme["tool_title"])
            self._emit(f"        {args_str}", style=self.theme["tool_body"])

    def show_tool_result(self, name: str, result: Any) -> None:
        self.thinking_stop()
        self._ensure_stream_closed()

        if isinstance(result, dict):
            rendered = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            rendered = str(result)
        rendered = rendered.strip() or "(empty)"
        lines = _truncate_lines(rendered.splitlines(), TOOL_RESULT_LINE_LIMIT)

        self._prefixed(PREFIX_RESULT, f"RESULT: {name}", self.theme["result_title"])
        for line in lines:
            self._emit(f"        {line}", style=self.theme["result_body"])

    # ── Goodbye ─────────────────────────────────────────────

    def goodbye(self) -> None:
        self._ensure_stream_closed()
        self.thinking_stop()
        self._emit("")
        self._rule()
        self._prefixed(PREFIX_STATUS, "session terminated.", self.theme["goodbye"])
        self._rule()

    # ── Internal: raw streaming (direct to stdout) ──────────

    def _raw_write(self, text: str) -> None:
        """Write text directly to terminal. Terminal handles wrapping."""
        self._raw_target.write(text)
        self._raw_target.flush()

    def _start_dim(self) -> None:
        """Apply ANSI dim+italic for reasoning text."""
        if not self._dim_active:
            self._raw_write(_ANSI_DIM_ITALIC)
            self._dim_active = True

    def _end_dim(self) -> None:
        """Reset ANSI styling after reasoning text."""
        if self._dim_active:
            self._raw_write(_ANSI_RESET)
            self._dim_active = False

    def _ensure_stream_closed(self) -> None:
        if self._phase == "idle":
            return
        self._end_dim()
        if self._phase not in ("idle", "started"):
            self._raw_write("\n")
        self._phase = "idle"
        self._at_line_start = False

    # ── Internal: encoding / sanitization ───────────────────

    def _detect_encoding(self) -> str:
        if self._use_rich and self.console is not None:
            target = getattr(self.console, "file", None) or sys.stdout
        else:
            target = sys.stdout
        encoding = (getattr(target, "encoding", None) or "utf-8").strip()
        return encoding or "utf-8"

    def _can_encode(self, text: str) -> bool:
        try:
            text.encode(self._encoding)
            return True
        except Exception:
            return False

    def _sanitize(self, text: str) -> str:
        try:
            text.encode(self._encoding)
            return text
        except Exception:
            return text.encode(self._encoding, errors="replace").decode(
                self._encoding, errors="replace"
            )

    # ── Internal: terminal output (Rich or plain) ──────────

    def _width(self) -> int:
        w = shutil.get_terminal_size((TERMINAL_FALLBACK_WIDTH, 20)).columns
        return max(TERMINAL_MIN_WIDTH, min(TERMINAL_MAX_WIDTH, w))

    def _emit(self, text: str, style: str = "", end: str = "\n") -> None:
        safe = self._sanitize(text)
        if self._use_rich and self.console is not None:
            self.console.print(
                safe,
                style=(style or None),
                end=end,
                markup=False,
                highlight=False,
                soft_wrap=True,
            )
            return
        print(safe, end=end, flush=True)

    def _prefixed(self, prefix: str, message: str, style: str = "") -> None:
        self._emit(f"  {prefix} {message}", style=style)

    def _rule(self, char: Optional[str] = None) -> None:
        bar = char or ("─" if self._unicode_ok else "-")
        self._emit(bar * self._width(), style=self.theme["rule"])
