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
import time
from typing import Any, Dict, List, Optional

from .__init__ import __version__
from .model_output_renderer import (
    LaneRenderable,
    ModelOutputRenderer,
    build_markdown_theme,
    build_palette,
    detect_theme_mode,
)

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.live import Live
    from rich.padding import Padding
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

_TOOL_CALL_LIVE_REFRESH_INTERVAL_SECONDS = 1 / 24
_TOOL_CALL_LIVE_PREVIEW_MAX_CHARS = 12_000
_TOOL_CALL_LIVE_PREVIEW_MIN_LINES = 8
_TOOL_CALL_LIVE_PREVIEW_MAX_LINES = 160

def _render_payload(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, indent=2)
        except TypeError:
            text = str(value)
    text = text.rstrip("\n")
    return text if text.strip() else "(empty)"


def _is_tool_result_error(value: Any) -> bool:
    if isinstance(value, dict):
        if "error" in value and value.get("error"):
            return True
        if "errors" in value and value.get("errors"):
            return True
        status = str(value.get("status", "")).strip().lower()
        if status in {"error", "failed", "failure"}:
            return True
        if "ok" in value and value.get("ok") is False:
            return True
        if "success" in value and value.get("success") is False:
            return True
        return False

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered.startswith("error:") or lowered.startswith("[error"):
            return True
        if "traceback" in lowered:
            return True

    return False


class ChatUI:
    """Terminal chat UI with tree-lane streaming output."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._use_rich = bool(
            HAS_RICH
            and getattr(sys.stdout, "isatty", lambda: False)()
            and getattr(sys.stdin, "isatty", lambda: False)()
        )
        # Keep Rich hard-wrap enabled so long streaming lines don't get clipped.
        self.console = Console() if self._use_rich else None

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
        self._tool_call_stream_open = False
        self._tool_call_stream_buffer = ""
        self._tool_call_stream_body_style = self.palette.tool_body
        self._tool_call_stream_prefix_style = self.palette.lane
        self._tool_call_stream_live = None
        self._tool_call_stream_last_refresh_at = 0.0
        self._tool_call_stream_live_show_full = False

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
                prompt_color = "#38c172" if self.palette.mode == "dark" else "#1f7f3e"
                line = self.console.input(f"[bold {prompt_color}]{prompt}[/bold {prompt_color}]")
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
        payload = _render_payload(arguments)
        self.tool_call_stream_start(name)
        self.tool_call_stream_token(payload)
        self.tool_call_stream_end()

    def tool_call_stream_start(self, name: str) -> None:
        self._ensure_stream_closed()
        self._emit_branch("├─ ", f"tool: {name}", message_style=self.palette.tool_title)
        self._tool_call_stream_open = True
        self._tool_call_stream_buffer = ""
        self._tool_call_stream_prefix_style = self.palette.lane
        self._tool_call_stream_last_refresh_at = 0.0
        self._tool_call_stream_live_show_full = False
        if self._use_rich and self.console is not None:
            self._tool_call_stream_body_style = (
                f"{self.palette.markdown_code_text} {self.palette.markdown_code_background}".strip()
            )
            self._start_tool_call_live()
        else:
            self._tool_call_stream_body_style = self.palette.tool_body
            self._emit_branch("│   ", "```", message_style=self.palette.tool_body)

    def tool_call_stream_token(self, token: str) -> None:
        if not token:
            return
        if not self._tool_call_stream_open:
            self.tool_call_stream_start("tool")
        if self._tool_call_stream_live is not None:
            self._tool_call_stream_buffer += self._sanitize(token)
            self._refresh_tool_call_live()
            return
        self._emit_stream_lines_with_lane(
            token,
            prefix="│   ",
            prefix_style=self._tool_call_stream_prefix_style,
            message_style=self._tool_call_stream_body_style,
            pending_attr="_tool_call_stream_buffer",
        )

    def tool_call_stream_end(self) -> None:
        if not self._tool_call_stream_open:
            return
        if self._tool_call_stream_live is not None:
            self._tool_call_stream_live_show_full = True
            self._stop_tool_call_live()
            self._tool_call_stream_open = False
            return
        pending = self._format_tool_call_stream_content(str(self._tool_call_stream_buffer or ""))
        if pending:
            self._emit_branch(
                "│   ",
                pending,
                message_style=self._tool_call_stream_body_style,
                prefix_style=self._tool_call_stream_prefix_style,
            )
            self._tool_call_stream_buffer = ""
        self._emit_branch(
            "│   ",
            "```",
            message_style=self.palette.tool_body,
            prefix_style=self._tool_call_stream_prefix_style,
        )
        self._tool_call_stream_open = False

    def _start_tool_call_live(self) -> None:
        if self.console is None or self._tool_call_stream_live is not None:
            return
        self._tool_call_stream_live = Live(
            self._build_tool_call_live_renderable(),
            console=self.console,
            refresh_per_second=20,
            transient=False,
            auto_refresh=False,
            vertical_overflow="crop",
        )
        self._tool_call_stream_live.start()
        self._refresh_tool_call_live(force=True)

    def _refresh_tool_call_live(self, *, force: bool = False) -> None:
        if self._tool_call_stream_live is None:
            return
        now = time.perf_counter()
        if not force and (now - self._tool_call_stream_last_refresh_at) < _TOOL_CALL_LIVE_REFRESH_INTERVAL_SECONDS:
            return
        self._tool_call_stream_last_refresh_at = now
        self._tool_call_stream_live.update(self._build_tool_call_live_renderable(), refresh=True)

    def _stop_tool_call_live(self) -> None:
        if self._tool_call_stream_live is None:
            return
        self._refresh_tool_call_live(force=True)
        self._tool_call_stream_live.stop()
        self._tool_call_stream_live = None
        self._tool_call_stream_last_refresh_at = 0.0

    def _build_tool_call_live_renderable(self):
        content = self._tool_call_stream_buffer if self._tool_call_stream_buffer else " "
        if self._tool_call_stream_live_show_full:
            content = self._format_tool_call_stream_content(content)
        else:
            content = self._tool_call_live_preview_content(content)
        code_text = Text(
            content,
            style=self._tool_call_stream_body_style,
            no_wrap=False,
            overflow="fold",
        )
        return LaneRenderable(
            Padding(code_text, (0, 1), style=self.palette.markdown_code_background),
            prefix="│   ",
            prefix_style=self._tool_call_stream_prefix_style,
            content_style=self._tool_call_stream_body_style,
        )

    def _tool_call_live_preview_content(self, content: str) -> str:
        preview = content
        if len(preview) > _TOOL_CALL_LIVE_PREVIEW_MAX_CHARS:
            preview = preview[-_TOOL_CALL_LIVE_PREVIEW_MAX_CHARS:]

        max_lines = self._tool_call_live_preview_line_budget(reserve_lines=4)
        lines = preview.splitlines()
        if preview.endswith("\n"):
            lines.append("")
        if len(lines) <= max_lines:
            return preview
        return "\n".join(lines[-max_lines:])

    def _tool_call_live_preview_line_budget(self, reserve_lines: int) -> int:
        available = max(_TOOL_CALL_LIVE_PREVIEW_MIN_LINES, self._terminal_height() - reserve_lines)
        return max(_TOOL_CALL_LIVE_PREVIEW_MIN_LINES, min(_TOOL_CALL_LIVE_PREVIEW_MAX_LINES, available))

    def _terminal_height(self) -> int:
        if self.console is not None:
            try:
                return max(12, int(self.console.size.height))
            except Exception:
                pass
        return 24

    def _format_tool_call_stream_content(self, content: str) -> str:
        text = content or ""
        stripped = text.strip()
        if not stripped:
            return text
        if not (stripped.startswith("{") or stripped.startswith("[")):
            return text
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return text
        if not isinstance(parsed, (dict, list)):
            return text
        try:
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return text

    def show_tool_result(self, name: str, result: Any) -> None:
        self._ensure_stream_closed()
        if _is_tool_result_error(result):
            self._emit_branch(
                "└─ ",
                f"result: {name}",
                message_style=self.palette.status_error,
                prefix_style=self.palette.status_error,
            )
            self._emit_tool_block(
                _render_payload(result),
                body_style=self.palette.result_body,
                prefix_style=self.palette.status_error,
            )
            return

        self._emit_branch("└─ ", f"result: {name}", message_style=self.palette.result_title)
        self._emit_branch(
            "│   ",
            "tool executed successfully.",
            message_style=self.palette.result_body,
        )

    def goodbye(self) -> None:
        self._ensure_stream_closed()
        self._emit_branch("└─ ", "session terminated.", message_style=self.palette.hint)

    def _ensure_stream_closed(self) -> None:
        if self._tool_call_stream_open:
            self.tool_call_stream_end()
        if self._renderer.active:
            # Preserve lifecycle color transitions for reasoning-only turns:
            # settle to success before tool/result blocks instead of dropping state.
            if self._renderer.reasoning_text and not self._renderer.output_text:
                self._renderer.finish_success()
            else:
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
                soft_wrap=False,
            )
            return
        print(safe, end=end, flush=True)

    def _emit_stream_lines_with_lane(
        self,
        text: str,
        *,
        prefix: str,
        prefix_style: str,
        message_style: str,
        pending_attr: str,
    ) -> None:
        pending = str(getattr(self, pending_attr, "")) + self._sanitize(text)
        parts = pending.split("\n")
        complete_lines = parts[:-1]
        tail = parts[-1]
        for line in complete_lines:
            self._emit_branch(
                prefix,
                line,
                message_style=message_style,
                prefix_style=prefix_style,
            )
        setattr(self, pending_attr, tail)

    def _emit_tool_block(self, text: str, *, body_style: str, prefix_style: str = "") -> None:
        safe = self._sanitize(text)
        lane_style = prefix_style or self.palette.lane
        if self._use_rich and self.console is not None:
            code_style = (
                f"{self.palette.markdown_code_text} {self.palette.markdown_code_background}".strip()
            )
            code_text = Text(
                safe,
                style=code_style,
                no_wrap=False,
                overflow="fold",
            )
            self.console.print(
                LaneRenderable(
                    Padding(code_text, (0, 1), style=self.palette.markdown_code_background),
                    prefix="│   ",
                    prefix_style=lane_style,
                    content_style=body_style,
                ),
                markup=False,
                highlight=False,
                soft_wrap=False,
            )
            return

        self._emit_branch("│   ", "```", message_style=body_style, prefix_style=lane_style)
        for line in safe.splitlines() or [""]:
            self._emit_branch("│   ", line, message_style=body_style, prefix_style=lane_style)
        self._emit_branch("│   ", "```", message_style=body_style, prefix_style=lane_style)

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
            self.console.print(line, end=end, markup=False, highlight=False, soft_wrap=False)
            return
        print(f"{prefix}{safe_message}", end=end, flush=True)
