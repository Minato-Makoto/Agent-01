"""
Model output renderer for tree-lane terminal UI.

Responsibilities:
- Detect effective UI theme mode (auto/dark/light)
- Build palette used by terminal rendering
- Render processing/thinking/output states as a minimal lane:
  - user line starts with `│`
  - status line starts with `├─`
  - assistant block starts with `└─`
- Stream markdown output in realtime with Rich Live updates
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.markdown import BlockQuote, CodeBlock, Heading, Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.segment import Segment
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme


THEME_MODE_AUTO = "auto"
THEME_MODE_DARK = "dark"
THEME_MODE_LIGHT = "light"


def detect_theme_mode(env: Optional[Mapping[str, str]] = None) -> str:
    """Detect UI theme mode with env override support."""
    source = env if env is not None else os.environ

    override = str(source.get("AGENTFORGE_UI_THEME", "")).strip().lower()
    if override in (THEME_MODE_DARK, THEME_MODE_LIGHT):
        return override
    if override and override != THEME_MODE_AUTO:
        return THEME_MODE_DARK

    colorfgbg = str(source.get("COLORFGBG", "")).strip()
    if colorfgbg:
        parts = colorfgbg.split(";")
        if parts:
            try:
                background_idx = int(parts[-1])
                # Conventional terminal palette: low indexes are dark backgrounds.
                return THEME_MODE_LIGHT if background_idx >= 8 else THEME_MODE_DARK
            except ValueError:
                pass

    term = " ".join(
        str(source.get(key, "")).strip().lower()
        for key in ("TERM", "COLORTERM", "TERM_PROGRAM")
    )
    if "light" in term:
        return THEME_MODE_LIGHT
    if "dark" in term:
        return THEME_MODE_DARK

    # Windows Terminal is overwhelmingly used with dark themes by default.
    if str(source.get("WT_SESSION", "")).strip():
        return THEME_MODE_DARK

    return THEME_MODE_DARK


@dataclass(frozen=True)
class UIPalette:
    mode: str
    code_theme: str
    lane: str
    user: str
    status_processing: str
    status_thinking: str
    status_success: str
    status_error: str
    assistant: str
    reasoning_text: str
    text: str
    hint: str
    banner: str
    tool_title: str
    tool_body: str
    result_title: str
    result_body: str
    markdown_inline_code: str
    markdown_em: str
    markdown_strong: str
    markdown_heading_h1: str
    markdown_heading_h2: str
    markdown_heading_h3: str
    markdown_quote_bar: str
    markdown_quote_text: str
    markdown_code_border: str
    markdown_code_background: str


def build_palette(mode: str) -> UIPalette:
    """Build palette for dark/light mode."""
    normalized = mode if mode in (THEME_MODE_DARK, THEME_MODE_LIGHT) else THEME_MODE_DARK
    if normalized == THEME_MODE_LIGHT:
        return UIPalette(
            mode=THEME_MODE_LIGHT,
            code_theme="friendly",
            lane="grey58",
            user="bold #0969da",
            status_processing="bold #9a6700",
            status_thinking="bold #9a6700",
            status_success="bold #1a7f37",
            status_error="bold #cf222e",
            assistant="bold #0969da",
            reasoning_text="#8250df",
            text="#24292f",
            hint="grey50",
            banner="bold #0969da",
            tool_title="bold #9a6700",
            tool_body="#57606a",
            result_title="bold #1a7f37",
            result_body="#57606a",
            markdown_inline_code="#24292f on #f6f8fa",
            markdown_em="italic #57606a",
            markdown_strong="bold #24292f",
            markdown_heading_h1="bold #0969da",
            markdown_heading_h2="bold #1f6feb",
            markdown_heading_h3="bold #0550ae",
            markdown_quote_bar="#9a6700",
            markdown_quote_text="#57606a",
            markdown_code_border="#d0d7de",
            markdown_code_background="on #f6f8fa",
        )
    return UIPalette(
        mode=THEME_MODE_DARK,
        code_theme="monokai",
        lane="grey58",
        user="bold bright_cyan",
        status_processing="bold yellow",
        status_thinking="bold yellow",
        status_success="bold green",
        status_error="bold red",
        assistant="bold bright_cyan",
        reasoning_text="italic bright_yellow",
        text="white",
        hint="grey62",
        banner="bold bright_cyan",
        tool_title="bold yellow",
        tool_body="grey70",
        result_title="bold green",
        result_body="grey70",
        markdown_inline_code="#f0f6fc on #30363d",
        markdown_em="italic grey78",
        markdown_strong="bold white",
        markdown_heading_h1="bold bright_cyan",
        markdown_heading_h2="bold cyan",
        markdown_heading_h3="bold bright_blue",
        markdown_quote_bar="bright_yellow",
        markdown_quote_text="grey78",
        markdown_code_border="#3d444d",
        markdown_code_background="on #161b22",
    )


def build_markdown_theme(palette: UIPalette) -> Theme:
    """Theme entries consumed by Rich markdown for inline styles."""
    return Theme(
        {
            "markdown.code": palette.markdown_inline_code,
            "markdown.em": palette.markdown_em,
            "markdown.strong": palette.markdown_strong,
            "markdown.link": "underline",
            "markdown.link_url": palette.hint,
            "markdown.item.bullet": palette.lane,
        }
    )


class LaneHeading(Heading):
    """Heading element aligned with tree-lane visual style."""

    @classmethod
    def create(cls, markdown: Markdown, token) -> "LaneHeading":
        palette = getattr(markdown, "palette", build_palette(THEME_MODE_DARK))
        return cls(token.tag, palette)

    def __init__(self, tag: str, palette: UIPalette) -> None:
        self.palette = palette
        super().__init__(tag)

    def __rich_console__(self, console: Console, options) -> RenderableType:
        text = self.text.copy()
        text.justify = "left"
        if self.tag == "h1":
            text.stylize(self.palette.markdown_heading_h1)
        elif self.tag == "h2":
            text.stylize(self.palette.markdown_heading_h2)
        else:
            text.stylize(self.palette.markdown_heading_h3)
        yield text


class LaneCodeBlock(CodeBlock):
    """Code block with rounded, dim panel."""

    @classmethod
    def create(cls, markdown: Markdown, token) -> "LaneCodeBlock":
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        palette = getattr(markdown, "palette", build_palette(THEME_MODE_DARK))
        return cls(lexer_name or "text", markdown.code_theme, palette)

    def __init__(self, lexer_name: str, theme: str, palette: UIPalette) -> None:
        super().__init__(lexer_name, theme)
        self.palette = palette

    def __rich_console__(self, console: Console, options) -> RenderableType:
        code = str(self.text).rstrip()
        syntax = Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=0)
        panel = Panel(
            syntax,
            box=box.ROUNDED,
            border_style=self.palette.markdown_code_border,
            style=self.palette.markdown_code_background,
            padding=(0, 1),
        )
        yield panel


class LaneBlockQuote(BlockQuote):
    """Block quote with IDE-like vertical lane marker."""

    @classmethod
    def create(cls, markdown: Markdown, token) -> "LaneBlockQuote":
        palette = getattr(markdown, "palette", build_palette(THEME_MODE_DARK))
        return cls(palette)

    def __init__(self, palette: UIPalette) -> None:
        super().__init__()
        self.palette = palette

    def __rich_console__(self, console: Console, options) -> RenderableType:
        render_options = options.update(width=max(12, options.max_width - 4))
        quote_style = console.get_style(self.palette.markdown_quote_text, default="dim")
        lines = console.render_lines(self.elements, render_options, style=quote_style)
        bar_style = console.get_style(self.palette.markdown_quote_bar, default=quote_style)
        lane = Segment("│ ", bar_style)
        new_line = Segment("\n")
        for line in lines:
            yield lane
            yield from line
            yield new_line


class LaneMarkdown(Markdown):
    """Markdown renderer customized for tree-lane terminal UI."""

    elements = dict(Markdown.elements)
    elements.update(
        {
            "heading_open": LaneHeading,
            "fence": LaneCodeBlock,
            "code_block": LaneCodeBlock,
            "blockquote_open": LaneBlockQuote,
        }
    )

    def __init__(self, markup: str, palette: UIPalette) -> None:
        self.palette = palette
        super().__init__(
            markup=markup,
            code_theme=palette.code_theme,
            style=palette.text,
            inline_code_theme=palette.code_theme,
        )


class ModelOutputRenderer:
    """Render model processing/thinking/output as a tree-lane stream."""

    def __init__(
        self,
        *,
        console: Optional[Console],
        use_rich: bool,
        palette: UIPalette,
    ) -> None:
        self._console = console
        self._use_rich = bool(use_rich and console is not None)
        self._palette = palette
        self._live: Optional[Live] = None

        self._active = False
        self._user_input = ""
        self._status_state = "idle"  # idle|processing|thinking|success|error
        self._reasoning_buffer = ""
        self._output_buffer = ""
        self._error_message = ""

        self._plain_reasoning_started = False
        self._plain_output_started = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def status_state(self) -> str:
        return self._status_state

    @property
    def reasoning_text(self) -> str:
        return self._reasoning_buffer

    @property
    def output_text(self) -> str:
        return self._output_buffer

    @property
    def error_message(self) -> str:
        return self._error_message

    def begin_turn(self, user_input: str) -> None:
        self.close()
        self._active = True
        self._user_input = user_input.strip()
        self._status_state = "processing"
        self._reasoning_buffer = ""
        self._output_buffer = ""
        self._error_message = ""
        self._plain_reasoning_started = False
        self._plain_output_started = False
        if self._use_rich:
            self._start_live()
            self._refresh()
        else:
            user = self._user_input if self._user_input else "(empty)"
            print(f"│ user: {user}", flush=True)

    def set_processing(self) -> None:
        if not self._active:
            return
        self._status_state = "processing"
        self._refresh()
        if not self._use_rich:
            self._plain_status("processing...", self._status_style())

    def append_reasoning(self, token: str) -> None:
        if not token:
            return
        if not self._active:
            self.begin_turn("")
        self._status_state = "thinking"
        self._reasoning_buffer += token
        self._refresh()
        if not self._use_rich:
            if not self._plain_reasoning_started:
                print("│ thinking: ", end="", flush=True)
                self._plain_reasoning_started = True
            print(token, end="", flush=True)

    def append_output(self, token: str) -> None:
        if not token:
            return
        if not self._active:
            self.begin_turn("")
        self._output_buffer += token
        self._refresh()
        if not self._use_rich:
            if not self._plain_output_started:
                if self._plain_reasoning_started:
                    print("", flush=True)
                print("└─ Agent-01:", flush=True)
                self._plain_output_started = True
            print(token, end="", flush=True)

    def finish_success(self) -> None:
        if not self._active:
            return
        self._status_state = "success"
        self._refresh()
        self._stop_live()
        if not self._use_rich:
            if self._plain_reasoning_started or self._plain_output_started:
                print("", flush=True)
            self._plain_status("completed.", self._status_style())
        self._active = False

    def finish_error(self, message: str) -> None:
        if not self._active:
            return
        self._status_state = "error"
        self._error_message = message.strip()
        self._refresh()
        self._stop_live()
        if not self._use_rich:
            if self._plain_reasoning_started or self._plain_output_started:
                print("", flush=True)
            self._plain_status(f"error: {self._error_message}", self._status_style())
        self._active = False

    def close(self) -> None:
        self._stop_live()
        self._active = False
        self._status_state = "idle"
        self._reasoning_buffer = ""
        self._output_buffer = ""
        self._error_message = ""
        self._plain_reasoning_started = False
        self._plain_output_started = False

    def _start_live(self) -> None:
        if self._live is not None or self._console is None:
            return
        self._live = Live(
            self._build_renderable(),
            console=self._console,
            refresh_per_second=20,
            transient=False,
            auto_refresh=False,
        )
        self._live.start()

    def _stop_live(self) -> None:
        if self._live is None:
            return
        self._live.stop()
        self._live = None

    def _refresh(self) -> None:
        if not self._use_rich or self._live is None:
            return
        self._live.update(self._build_renderable(), refresh=True)

    def _status_style(self) -> str:
        if self._status_state == "success":
            return self._palette.status_success
        if self._status_state == "error":
            return self._palette.status_error
        if self._status_state == "thinking":
            return self._palette.status_thinking
        return self._palette.status_processing

    def _status_text(self) -> str:
        if self._status_state == "success":
            return "completed."
        if self._status_state == "error":
            return f"error: {self._error_message}" if self._error_message else "error."
        if self._status_state == "thinking":
            return "thinking..."
        return "processing..."

    def _build_renderable(self) -> RenderableType:
        user = self._user_input if self._user_input else "(empty)"
        blocks: list[RenderableType] = [
            Text(f"│ user: {user}", style=self._palette.user),
            Text(f"├─ {self._status_text()}", style=self._status_style()),
        ]

        if self._reasoning_buffer:
            blocks.append(Text("│", style=self._palette.lane))
            blocks.append(Text("│ thinking", style=self._palette.status_thinking))
            blocks.append(
                Padding(
                    Text(self._reasoning_buffer, style=self._palette.reasoning_text, overflow="fold"),
                    (0, 2, 0, 2),
                )
            )

        if self._output_buffer:
            blocks.append(Text("│", style=self._palette.lane))
            blocks.append(Text("└─ Agent-01", style=self._palette.assistant))
            blocks.append(Padding(LaneMarkdown(self._output_buffer, self._palette), (0, 2, 0, 2)))
        elif self._status_state == "error" and self._error_message:
            blocks.append(Text("│", style=self._palette.lane))
            blocks.append(Text(f"└─ {self._error_message}", style=self._palette.status_error))

        return Group(*blocks)

    def _plain_status(self, text: str, style: str) -> None:
        del style
        print(f"├─ {text}", flush=True)
