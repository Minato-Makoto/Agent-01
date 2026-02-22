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


def test_tool_call_stream_formatter_prettifies_complete_json():
    ui = ChatUI(verbose=False)
    rendered = ui._format_tool_call_stream_content('{"path":"workspace/AGENT.md","mode":"read"}')
    assert "\n" in rendered
    assert '"path": "workspace/AGENT.md"' in rendered


def test_tool_call_stream_formatter_keeps_partial_json_raw():
    ui = ChatUI(verbose=False)
    raw = '{"path":"workspace/AGENT.md"'
    rendered = ui._format_tool_call_stream_content(raw)
    assert rendered == raw


def test_tool_call_live_uses_crop_vertical_overflow(monkeypatch):
    captured = {"kwargs": {}, "started": 0}

    class _FakeConsole:
        def __init__(self, *args, **kwargs):
            del args, kwargs
            self.file = sys.stdout

        def push_theme(self, theme):
            del theme

        def print(self, *args, **kwargs):
            del args, kwargs

    class _FakeLive:
        def __init__(self, renderable, **kwargs):
            del renderable
            captured["kwargs"] = kwargs

        def start(self):
            captured["started"] += 1

        def update(self, renderable, refresh):
            del renderable, refresh

        def stop(self):
            return None

    monkeypatch.setattr(ui_module, "HAS_RICH", True)
    monkeypatch.setattr(ui_module, "Console", _FakeConsole)
    monkeypatch.setattr(ui_module, "Live", _FakeLive)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)

    ui = ChatUI(verbose=False)
    ui.tool_call_stream_start("read_file")

    assert captured["started"] == 1
    assert captured["kwargs"]["vertical_overflow"] == "crop"


def test_tool_call_live_preview_tracks_tail_lines():
    ui = ChatUI(verbose=False)

    class _FakeConsole:
        class _Size:
            height = 12

        size = _Size()

    ui.console = _FakeConsole()
    text = "\n".join(f"line {idx}" for idx in range(20))
    preview = ui._tool_call_live_preview_content(text)

    assert preview.startswith("line 12")
    assert preview.endswith("line 19")
    assert "line 0" not in preview


def test_tool_call_live_refresh_throttles_rapid_updates(monkeypatch):
    ui = ChatUI(verbose=False)
    ui._tool_call_stream_buffer = '{"x": 1}'

    class _LiveStub:
        def __init__(self):
            self.calls = 0

        def update(self, renderable, refresh):
            del renderable, refresh
            self.calls += 1

        def stop(self):
            return None

    live = _LiveStub()
    ui._tool_call_stream_live = live

    ticks = iter([10.0, 10.001, 10.2])
    monkeypatch.setattr("agentforge.ui.time.perf_counter", lambda: next(ticks))

    ui._refresh_tool_call_live()
    ui._refresh_tool_call_live()
    ui._refresh_tool_call_live()

    assert live.calls == 2
