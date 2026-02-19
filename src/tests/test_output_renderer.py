from rich.console import Console

from agentforge.model_output_renderer import (
    LaneMarkdown,
    ModelOutputRenderer,
    build_palette,
    detect_theme_mode,
)


def test_detect_theme_mode_override():
    assert detect_theme_mode({"AGENTFORGE_UI_THEME": "dark"}) == "dark"
    assert detect_theme_mode({"AGENTFORGE_UI_THEME": "light"}) == "light"
    assert detect_theme_mode({"AGENTFORGE_UI_THEME": "invalid"}) == "dark"


def test_detect_theme_mode_from_colorfgbg():
    assert detect_theme_mode({"AGENTFORGE_UI_THEME": "auto", "COLORFGBG": "0;15"}) == "light"
    assert detect_theme_mode({"AGENTFORGE_UI_THEME": "auto", "COLORFGBG": "15;0"}) == "dark"


def test_build_palette_returns_mode_specific_defaults():
    dark = build_palette("dark")
    light = build_palette("light")
    assert dark.mode == "dark"
    assert light.mode == "light"
    assert dark.code_theme != light.code_theme


def test_renderer_state_transitions_without_rich():
    renderer = ModelOutputRenderer(
        console=None,
        use_rich=False,
        palette=build_palette("dark"),
    )
    renderer.begin_turn("hello")
    renderer.set_processing()
    renderer.append_reasoning("r1")
    renderer.append_output("ok")
    assert renderer.active is True
    assert renderer.status_state == "thinking"
    assert renderer.reasoning_text == "r1"
    assert renderer.output_text == "ok"

    renderer.finish_success()
    assert renderer.active is False
    assert renderer.status_state == "success"


def test_lane_markdown_quote_and_codeblock_shapes():
    palette = build_palette("dark")
    markdown = LaneMarkdown("> quoted line\n\n```python\nprint('x')\n```", palette)
    console = Console(record=True, width=80)
    console.print(markdown)
    text = console.export_text()
    assert "│ quoted line" in text
    assert ("╭" in text) or ("┌" in text)
    assert ("╰" in text) or ("└" in text)
