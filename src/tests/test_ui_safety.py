import sys

import agentforge.ui as ui_module
from agentforge.ui import ChatUI


def test_ui_sanitize_replaces_unencodable_text():
    ui = ChatUI(verbose=False)
    ui._encoding = "ascii"
    out = ui._sanitize("ok🙂")
    assert "ok" in out


def test_ui_stream_lifecycle_resets_internal_state():
    ui = ChatUI(verbose=False)
    ui.stream_start()
    ui.stream_reasoning("r")
    ui.stream_token("a")
    ui.stream_end()
    assert ui._phase == "idle"
    assert ui._dim_active is False


def test_ui_error_closes_active_lane():
    ui = ChatUI(verbose=False)
    ui._last_user_input = "hello"
    ui.thinking_start()
    ui.stream_reasoning("x")
    ui.error("boom")
    assert ui._phase == "idle"
    assert ui._renderer.active is False


def test_ui_does_not_echo_user_input_in_output_lane():
    ui = ChatUI(verbose=False)
    ui._last_user_input = "secret prompt"
    ui.thinking_start()
    ui.stream_reasoning("plan")
    ui.stream_token("done")

    assert "secret prompt" not in ui._renderer.reasoning_text
    assert "secret prompt" not in ui._renderer.output_text


def test_chatui_rich_console_does_not_enable_soft_wrap(monkeypatch):
    class _FakeConsole:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs
            self.file = sys.stdout

        def push_theme(self, theme):
            del theme

    monkeypatch.setattr(ui_module, "HAS_RICH", True)
    monkeypatch.setattr(ui_module, "Console", _FakeConsole)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)

    ui = ChatUI(verbose=False)
    assert ui._use_rich is True
    assert isinstance(ui.console, _FakeConsole)
    assert "soft_wrap" not in ui.console.kwargs


def test_goodbye_does_not_emit_leading_blank_line(monkeypatch):
    ui = ChatUI(verbose=False)
    emitted = []

    monkeypatch.setattr(ui, "_emit", lambda *args, **kwargs: emitted.append(("emit", args, kwargs)))
    monkeypatch.setattr(
        ui,
        "_emit_branch",
        lambda prefix, message, **kwargs: emitted.append(("branch", prefix, message, kwargs)),
    )

    ui.goodbye()
    assert emitted
    first = emitted[0]
    assert first[0] == "branch"
    assert first[1] == "└─ "
    assert first[2] == "session terminated."
