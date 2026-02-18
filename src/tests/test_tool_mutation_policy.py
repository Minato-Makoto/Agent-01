from agentforge.tool_mutation import is_mutating_tool_call


def test_read_only_tool_is_not_mutating():
    assert is_mutating_tool_call("read_file", {"path": "C:/tmp/a.txt"}) is False


def test_message_tool_with_content_is_mutating():
    assert is_mutating_tool_call("message", {"content": "ship it"}) is True


def test_process_poll_action_is_not_mutating():
    assert is_mutating_tool_call("process", {"action": "status"}) is False


def test_process_kill_action_is_mutating():
    assert is_mutating_tool_call("process", {"action": "kill"}) is True
