from agentforge.agent_core import Agent, AgentConfig
from agentforge.contracts import ChatCompletionResult
from agentforge.tools import ToolRegistry


class _DoneLLM:
    def __init__(self):
        self.capabilities = type("Caps", (), {"supports_tools": True})()

    def chat_completion(self, messages, **kwargs):
        del messages, kwargs
        return ChatCompletionResult(content="done", finish_reason="stop")


def test_bootstrap_tools_only_register_read_file(minimal_workspace):
    agent = Agent(
        config=AgentConfig(workspace_dir=str(minimal_workspace), max_iterations=2),
        llm=_DoneLLM(),
        tools=ToolRegistry(),
    )

    assert agent.tools.find("read_file") is not None
    assert agent.tools.find("think") is None
