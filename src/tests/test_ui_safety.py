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
