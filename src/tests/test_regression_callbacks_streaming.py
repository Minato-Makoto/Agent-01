import json

from agentforge.agent_core import Agent, AgentConfig, StreamCallbacks
from agentforge.contracts import ChatCompletionResult, ToolCall
from agentforge.llm_inference import InferenceConfig, LLMInference
from agentforge.tools import Tool, ToolRegistry


def test_streaming_tokens_and_reasoning_are_preserved(mock_chat_server):
    llm = LLMInference()
    assert llm.connect_remote(
        base_url=mock_chat_server.url,
        model_id="mock",
        config=InferenceConfig(max_tokens=64),
    )

    mock_chat_server.enqueue_stream(
        [
            {
                "choices": [
                    {"delta": {"reasoning_content": "thinking..."}, "finish_reason": None}
                ]
            },
            {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}]},
        ]
    )

    tokens = []
    reasoning = []
    result = llm.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
        on_token=tokens.append,
        on_reasoning=reasoning.append,
    )

    assert result.error == ""
    assert result.content == "Hello world"
    assert "".join(tokens) == "Hello world"
    assert "".join(reasoning) == "thinking..."


class _FakeLLM:
    def __init__(self):
        self.capabilities = type("Caps", (), {"supports_tools": True})()
        self._round = 0

    def chat_completion(self, messages, **kwargs):
        self._round += 1
        if self._round == 1:
            return ChatCompletionResult(
                content="",
                tool_calls=[ToolCall(id="call-1", name="noop_tool", arguments={"x": 1})],
                finish_reason="tool_calls",
            )
        on_token = kwargs.get("on_token")
        on_reasoning = kwargs.get("on_reasoning")
        if on_reasoning:
            on_reasoning("r")
        if on_token:
            on_token("done")
        return ChatCompletionResult(content="done", finish_reason="stop")


def test_agent_ui_callbacks_regression(minimal_workspace):
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="noop_tool",
            description="returns ok",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
            execute_fn=lambda args: {"ok": args["x"]},
        )
    )
    agent = Agent(
        config=AgentConfig(workspace_dir=str(minimal_workspace), max_iterations=4),
        llm=_FakeLLM(),
        tools=registry,
    )

    events = {
        "start": 0,
        "end": 0,
        "tool_calls": [],
        "tool_results": [],
        "tokens": [],
        "reasoning": [],
    }
    callbacks = StreamCallbacks(
        on_stream_start=lambda: events.__setitem__("start", events["start"] + 1),
        on_stream_end=lambda: events.__setitem__("end", events["end"] + 1),
        on_tool_call=lambda name, args: events["tool_calls"].append((name, args)),
        on_tool_result=lambda name, out: events["tool_results"].append((name, out)),
        on_token=events["tokens"].append,
        on_reasoning=events["reasoning"].append,
    )

    answer = agent.run("go", callbacks=callbacks)
    assert answer == "done"
    # on_stream_start is now a UI concern (triggered lazily by stream_token),
    # so the agent loop does not call it directly.
    assert events["end"] == 2
    assert len(events["tool_calls"]) == 1
    assert events["tool_calls"][0][0] == "noop_tool"
    assert len(events["tool_results"]) == 1
    assert "".join(events["tokens"]) == "done"
    assert "".join(events["reasoning"]) == "r"
