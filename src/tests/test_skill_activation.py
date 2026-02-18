from pathlib import Path

from agentforge.agent_core import Agent, AgentConfig
from agentforge.contracts import ChatCompletionResult
from agentforge.skills import SkillLoader
from agentforge.tools import ToolRegistry


class _DummyLLM:
    def __init__(self):
        self.capabilities = type("Caps", (), {"supports_tools": True})()

    def chat_completion(self, **kwargs):
        return ChatCompletionResult(content="ok")


def _write_skill_file(path: Path) -> Path:
    skill_dir = path / "skills" / "math"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL_MATH.md"
    skill_file.write_text(
        """---
name: Math
description: Math operations
tools:
  - calculate
module: builtin_tools.calculator
---
# Math skill
""",
        encoding="utf-8",
    )
    return skill_file


def test_skill_is_unavailable_until_activation_then_unlocked(minimal_workspace):
    skill_file = _write_skill_file(minimal_workspace)
    loader = SkillLoader(str(minimal_workspace))
    discovered = loader.discover()
    assert "Math" in discovered

    registry = ToolRegistry()
    agent = Agent(
        config=AgentConfig(workspace_dir=str(minimal_workspace), max_iterations=2),
        llm=_DummyLLM(),
        tools=registry,
        skill_loader=loader,
    )

    before = agent.tool_loop.execute_tool("calculate", {"expression": "1+1"})
    assert before.success is False
    assert "not found" in before.error

    read_file_tool = registry.find("read_file")
    assert read_file_tool is not None
    read_result = read_file_tool.execute({"path": str(skill_file)})
    assert read_result.success is True
    assert registry.has("calculate")
    after = agent.tool_loop.execute_tool("calculate", {"expression": "1+1"})
    assert after.success is True
    assert after.output["result"] == 2
