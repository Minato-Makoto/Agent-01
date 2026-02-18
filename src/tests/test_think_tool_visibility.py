from agentforge.agent_core import Agent, AgentConfig, StreamCallbacks
from agentforge.contracts import ChatCompletionResult, ToolCall
from agentforge.tools import ToolRegistry


class _ThinkLLM:
    def __init__(self):
        self.capabilities = type("Caps", (), {"supports_tools": True})()
        self._round = 0

    def chat_completion(self, messages, **kwargs):
        self._round += 1
        if self._round == 1:
            return ChatCompletionResult(
                content="",
                tool_calls=[ToolCall(id="call_1", name="think", arguments={"thought": "plan A"})],
                finish_reason="tool_calls",
            )
        return ChatCompletionResult(content="done", finish_reason="stop")


def test_think_tool_output_is_visible_to_user(minimal_workspace):
    agent = Agent(
        config=AgentConfig(workspace_dir=str(minimal_workspace), max_iterations=4),
        llm=_ThinkLLM(),
        tools=ToolRegistry(),
    )

    tool_results = []
    callbacks = StreamCallbacks(on_tool_result=lambda name, out: tool_results.append((name, out)))
    answer = agent.run("start", callbacks=callbacks)

    assert answer == "done"
    think_results = [out for name, out in tool_results if name == "think"]
    assert len(think_results) == 1
    assert "Thought: plan A" in think_results[0]

