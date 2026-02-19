"""
AgentForge terminal chat UI.

Design:
- Keep ASCII banner identity
- Tree-lane output (`│`, `├─`, `└─`) for status/progress
- Realtime markdown rendering for model output via ModelOutputRenderer
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, List, Optional

from .__init__ import __version__
from .model_output_renderer import (
    ModelOutputRenderer,
    build_markdown_theme,
    build_palette,
    detect_theme_mode,
)

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


_BANNER_LINES = r"""
    ___                    __  ______
   /   | ____ ____  ____  / /_/ ____/___  _________ ____
  / /| |/ __ `/ _ \/ __ \/ __/ /_  / __ \/ ___/ __ `/ _ \
 / ___ / /_/ /  __/ / / / /_/ __/ / /_/ / /  / /_/ /  __/
/_/  |_\__, /\___/_/ /_/\__/_/    \____/_/   \__, /\___/
      /____/                                /____/
"""

TOOL_RESULT_LINE_LIMIT = 15


def _short(value: Any, limit: int = 80) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _truncate_lines(lines: List[str], limit: int) -> List[str]:
    if len(lines) <= limit:
        return lines
    return lines[:limit] + ["... (truncated)"]


class ChatUI:
    """Terminal chat UI with tree-lane streaming output."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._use_rich = bool(
            HAS_RICH
            and getattr(sys.stdout, "isatty", lambda: False)()
            and getattr(sys.stdin, "isatty", lambda: False)()
        )
        self.console = Console(soft_wrap=True) if self._use_rich else None

        theme_mode = detect_theme_mode()
        self.palette = build_palette(theme_mode)
        if self.console is not None:
            self.console.push_theme(build_markdown_theme(self.palette))

        self._renderer = ModelOutputRenderer(
            console=self.console,
            use_rich=self._use_rich,
            palette=self.palette,
        )

        # Stream lifecycle retained for callback compatibility/tests.
        self._phase = "idle"
        self._dim_active = False
        self._assistant_buffer = ""
        self._last_user_input = ""

        self._encoding = self._detect_encoding()

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
        del tools
        banner_lines = _BANNER_LINES.strip("\n").splitlines()
        banner_width = max((len(line.rstrip()) for line in banner_lines), default=0)
        for line in banner_lines:
            self._emit(line, style=self.palette.banner)
        self._emit(f"v{__version__}".rjust(banner_width), style=self.palette.hint)
        self._emit_branch("│ ", f"model: {model_name}", message_style=self.palette.text)
        if session_id:
            self._emit_branch("│ ", f"session: {session_id}", message_style=self.palette.hint)
        if self.verbose:
            if provider:
                self._emit_branch("│ ", f"runtime: {provider}", message_style=self.palette.text)
            self._emit_branch(
                "│ ",
                f"tools: {skill_count} skills ({total_tool_count} total tools)",
                message_style=self.palette.hint,
            )
            if workspace:
                self._emit_branch("│ ", f"workspace: {workspace}", message_style=self.palette.hint)
        self._emit_branch(
            "│ ",
            "commands: exit | reset | clear | skills | session",
            message_style=self.palette.hint,
        )
        self._emit("")

    def status(self, msg: str) -> None:
        self._ensure_stream_closed()
        self._emit_branch("│ ", msg, message_style=self.palette.hint)

    def error(self, msg: str) -> None:
        if self._renderer.active:
            self._renderer.finish_error(msg)
        else:
            self._emit(f"└─ error: {msg}", style=self.palette.status_error)
        self._phase = "idle"
        self._dim_active = False
        self._assistant_buffer = ""

    def log(self, msg: str) -> None:
        if not self.verbose:
            return
        self._ensure_stream_closed()
        self._emit_branch("│ ", f"debug: {msg}", message_style=self.palette.hint)

    def get_input(self) -> Optional[str]:
        prompt = "> "
        try:
            if self._use_rich and self.console is not None:
                line = self.console.input(f"[bold bright_green]{prompt}[/bold bright_green]")
            else:
                line = input(prompt)
            value = line.strip()
            self._last_user_input = value
            return value
        except (EOFError, KeyboardInterrupt):
            return None

    def thinking_start(self) -> None:
        if not self._renderer.active:
            self._renderer.begin_turn(self._last_user_input)
        self._renderer.set_processing()
        if self._phase == "idle":
            self._phase = "started"

    def thinking_stop(self) -> None:
        return

    def stream_start(self) -> None:
        if not self._renderer.active:
            self._renderer.begin_turn(self._last_user_input)
        self._phase = "started"
        self._assistant_buffer = ""

    def stream_token(self, token: str) -> None:
        if not token:
            return
        if self._phase == "idle":
            self.stream_start()
        if self._phase in ("idle", "started", "reasoning"):
            self._phase = "assistant"
            self._dim_active = False
        self._assistant_buffer += token
        self._renderer.append_output(token)

    def stream_reasoning(self, token: str) -> None:
        if not token:
            return
        if self._phase == "idle":
            self.stream_start()
        self._phase = "reasoning"
        self._dim_active = True
        self._renderer.append_reasoning(token)

    def stream_end(self) -> None:
        if self._renderer.active:
            self._renderer.finish_success()
        self._assistant_buffer = ""
        self._phase = "idle"
        self._dim_active = False

    def show_tool_call(self, name: str, arguments: Dict[str, Any]) -> None:
        self._ensure_stream_closed()
        if not arguments:
            self._emit_branch("├─ ", f"tool: {name}()", message_style=self.palette.tool_title)
            return
        args_str = _short(arguments, 72)
        self._emit_branch("├─ ", f"tool: {name}", message_style=self.palette.tool_title)
        self._emit_branch("│   ", args_str, message_style=self.palette.tool_body)

    def show_tool_result(self, name: str, result: Any) -> None:
        self._ensure_stream_closed()

        if isinstance(result, dict):
            rendered = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            rendered = str(result)
        rendered = rendered.strip() or "(empty)"
        lines = _truncate_lines(rendered.splitlines(), TOOL_RESULT_LINE_LIMIT)

        self._emit_branch("└─ ", f"result: {name}", message_style=self.palette.result_title)
        for line in lines:
            self._emit_branch("│   ", line, message_style=self.palette.result_body)

    def goodbye(self) -> None:
        self._ensure_stream_closed()
        self._emit("")
        self._emit_branch("└─ ", "session terminated.", message_style=self.palette.hint)

    def _ensure_stream_closed(self) -> None:
        if self._renderer.active:
            self._renderer.close()
        self._phase = "idle"
        self._dim_active = False
        self._assistant_buffer = ""

    def _detect_encoding(self) -> str:
        if self._use_rich and self.console is not None:
            target = getattr(self.console, "file", None) or sys.stdout
        else:
            target = sys.stdout
        encoding = (getattr(target, "encoding", None) or "utf-8").strip()
        return encoding or "utf-8"

    def _sanitize(self, text: str) -> str:
        try:
            text.encode(self._encoding)
            return text
        except (LookupError, UnicodeEncodeError):
            return text.encode(self._encoding, errors="replace").decode(
                self._encoding, errors="replace"
            )

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

    def _emit_branch(
        self,
        prefix: str,
        message: str,
        *,
        message_style: str = "",
        prefix_style: str = "",
        end: str = "\n",
    ) -> None:
        safe_message = self._sanitize(message)
        lane_style = prefix_style or self.palette.lane
        if self._use_rich and self.console is not None:
            line = Text()
            line.append(prefix, style=lane_style)
            line.append(safe_message, style=(message_style or self.palette.text))
            self.console.print(line, end=end, markup=False, highlight=False, soft_wrap=True)
            return
        print(f"{prefix}{safe_message}", end=end, flush=True)
