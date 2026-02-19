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
