from agentforge.tool_call_parser import ToolCallParser


def test_fallback_parser_prefers_tool_call_block():
    parser = ToolCallParser()
    result = parser.parse(
        '<tool_call>{"name":"read_file","arguments":{"path":"C:/tmp/a.txt"}}</tool_call>'
    )
    assert result.has_tool_calls
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments["path"] == "C:/tmp/a.txt"


def test_fallback_parser_supports_bare_json_object():
    parser = ToolCallParser()
    result = parser.parse('{"name":"think","arguments":{"thought":"plan"}}')
    assert result.has_tool_calls
    assert result.tool_calls[0].name == "think"


def test_fallback_parser_plain_text_has_no_tool_call():
    parser = ToolCallParser()
    result = parser.parse("No tools needed.")
    assert not result.has_tool_calls
