from agentforge.context import ContextBuilder
from agentforge.memory import MemoryStore


def test_memory_section_header_is_not_duplicated(tmp_path):
    for name in ("IDENTITY.md", "SOUL.md", "AGENT.md", "USER.md"):
        (tmp_path / name).write_text("", encoding="utf-8")

    mem = MemoryStore(str(tmp_path))
    mem.write_long_term("# Long-term Memory\n\nremember this")
    memory_context = mem.get_memory_context()

    builder = ContextBuilder(str(tmp_path))
    prompt = builder.build_system_prompt(memory_context=memory_context)
    assert prompt.count("# Memory") == 1
