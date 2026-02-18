from agentforge.tools import Tool


async def _async_tool_impl(args):
    return {"echo": args.get("value")}


def test_tool_execute_supports_async_return_in_sync_runtime():
    tool = Tool(
        name="async_echo",
        description="async echo",
        input_schema={"type": "object", "properties": {"value": {"type": "string"}}},
        execute_fn=_async_tool_impl,
    )

    result = tool.execute({"value": "ok"})
    assert result.success is True
    assert result.output == {"echo": "ok"}

