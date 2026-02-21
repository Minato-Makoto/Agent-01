"""
simulate_context.py — Event driver cho Agent-01

File này CHỈ tạo event (user messages) để kích hoạt source code thật.
Mọi logic (summarization, branching, hydration, prompt building...)
đều chạy từ src/agentforge/ — không viết lại bất kỳ logic nào ở đây.

MockLLM chỉ làm 2 việc:
  1. In ra payload mà source code gửi cho model
  2. Trả về response giả để source code tiếp tục chạy
"""

import json
import sys
import tempfile
from pathlib import Path

# --- Import thật từ source code ---
from agentforge.agent_core import Agent, AgentConfig, StreamCallbacks
from agentforge.context import ContextBuilder
from agentforge.contracts import ChatCompletionResult, ProviderCapabilities
from agentforge.session import SessionManager
from agentforge.summarizer import Summarizer
from agentforge.tools import Tool, ToolRegistry, ToolResult


class MockLLM:
    """
    Thay thế LLMInference — KHÔNG chứa logic nào.
    Chỉ in payload nhận được và trả response giả.
    """

    def __init__(self, *, token_limit: int = 0):
        # Source code đọc field này để biết provider hỗ trợ gì
        self.capabilities = ProviderCapabilities(supports_tools=True)
        self.model_desc = "MockLLM"
        self._call = 0
        self._token_limit = token_limit

    def chat_completion(self, messages, **kwargs):
        """Source code gọi method này mỗi turn — ta chỉ in và trả giả."""
        self._call += 1
        clean = [{k: v for k, v in m.items() if v is not None and v != ""} for m in messages]
        total = sum(len(json.dumps(m, ensure_ascii=False)) for m in clean)
        print(f"\n{'═' * 80}")
        print(f"  [chat_completion #{self._call}] {len(clean)} messages, ~{total} chars")
        print(f"{'═' * 80}")
        print(json.dumps(clean, indent=2, ensure_ascii=False))
        if kwargs.get("tools"):
            print(f"  + {len(kwargs['tools'])} tool(s) đính kèm")
        print()

        if self._token_limit and total > self._token_limit:
            print(f"  ✗ FAKE REJECT: {total} > {self._token_limit}\n")
            return ChatCompletionResult(content="", error="context_length_exceeded")

        return ChatCompletionResult(content=f"[Mock #{self._call}]")

    def generate(self, prompt: str, **kwargs):
        """Source code gọi method này khi Graceful Summarize cần LLM — ta trả summary giả."""
        self._call += 1
        print(f"\n{'─' * 80}")
        print(f"  [generate #{self._call}] Summarization prompt ({len(prompt)} chars):")
        print(f"{'─' * 80}")
        # In 400 char đầu để thấy prompt mà source code tạo ra
        print(prompt[:400] + ("..." if len(prompt) > 400 else ""))
        print()
        return (
            "1) Goal: Hỗ trợ user.\n"
            "2) Decisions: Đã xử lý các yêu cầu trước.\n"
            "3) File/tool state: Không có pending.\n"
            "4) Pending work: Chờ chỉ thị.\n"
            "5) Constraints: Context đã nén."
        )


def _make_tools() -> ToolRegistry:
    """Đăng ký 1 tool giả để test tool-call flow."""
    reg = ToolRegistry()
    reg.register(
        Tool(
            name="dummy_read_file",
            description="Đọc file giả lập.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            execute_fn=lambda args: ToolResult(
                success=True, output="FILE_START\n" + ("A" * 2000) + "\nFILE_END"
            ),
        )
    )
    return reg


def _sep(title: str):
    print(f"\n{'█' * 80}")
    print(f"  {title}")
    print(f"{'█' * 80}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    workspace = str(Path(__file__).parent / "workspace")

    with tempfile.TemporaryDirectory() as tmp:
        # ──────────────────────────────────────────────────
        # DEMO 1: Normal flow — xem model nhận gì
        # ──────────────────────────────────────────────────
        _sep("DEMO 1: Normal conversation")

        mgr = SessionManager(tmp)
        mgr.new_session()

        agent = Agent(
            config=AgentConfig(workspace_dir=workspace, max_iterations=2),
            llm=MockLLM(),
            tools=_make_tools(),
            session_mgr=mgr,
            summarizer=Summarizer(max_tokens=8000),
            context_builder=ContextBuilder(workspace),
        )

        for msg in ["Xin chào", "Hôm nay làm gì?"]:
            print(f">>> [USER]: {msg}")
            r = agent.run(msg)
            print(f"<<< [AGENT]: {r}\n")

        # ──────────────────────────────────────────────────
        # DEMO 2: Bơm nhiều tin nhắn → kích hoạt Tier 1
        # ──────────────────────────────────────────────────
        _sep("DEMO 2: Graceful Summarization + Session Branch")

        mgr2 = SessionManager(tmp + "/branch")
        mgr2.new_session()
        old_id = mgr2.session.id

        agent2 = Agent(
            config=AgentConfig(workspace_dir=workspace, max_iterations=2),
            llm=MockLLM(),
            tools=_make_tools(),
            session_mgr=mgr2,
            # max_tokens rất nhỏ để ép Tier 1 kích hoạt sớm
            summarizer=Summarizer(max_tokens=120, chars_per_token=4),
            context_builder=ContextBuilder(workspace),
        )

        for i in range(5):
            msg = f"Tin nhắn #{i+1}: " + ("X" * 60)
            print(f">>> [USER]: {msg[:50]}...")
            r = agent2.run(msg)
            print(f"<<< [AGENT]: {r}")

        new_id = mgr2.session.id
        print(f"\n[INFO] old_session = {old_id}")
        print(f"[INFO] new_session = {new_id}")
        print(f"[INFO] previous_session_id = {mgr2.session.previous_session_id}")
        print(f"[INFO] Branch: {'✓ OK' if new_id != old_id else '✗ Không branch'}")

        # ──────────────────────────────────────────────────
        # DEMO 3: Load session cũ → hydration
        # ──────────────────────────────────────────────────
        _sep("DEMO 3: Session Hydration")

        mgr3 = SessionManager(tmp + "/branch")
        loaded = mgr3.load_session(new_id)
        print(f"[INFO] Loaded session {new_id}: {len(loaded.messages)} messages")
        print(f"[INFO] previous_session_id: {loaded.previous_session_id}")

        agent3 = Agent(
            config=AgentConfig(workspace_dir=workspace, max_iterations=2),
            llm=MockLLM(),
            tools=_make_tools(),
            session_mgr=mgr3,
            summarizer=Summarizer(max_tokens=8000),
            context_builder=ContextBuilder(workspace),
        )

        print(f"\n>>> [USER]: Nhắc lại context cũ đi")
        r = agent3.run("Nhắc lại context cũ đi")
        print(f"<<< [AGENT]: {r}")
        print(f"\n[INFO] Prompt messages: {len(agent3.prompt.messages)}")
        print(f"[INFO] Hydration: {'✓ OK' if len(agent3.prompt.messages) > 2 else '✗ Thiếu'}")

        # ──────────────────────────────────────────────────
        # DEMO 4: Emergency compress (Tier 2)
        # ──────────────────────────────────────────────────
        _sep("DEMO 4: Emergency Compression (Tier 2)")

        mgr4 = SessionManager(tmp + "/emergency")
        mgr4.new_session()

        # MockLLM luôn reject → source code sẽ gọi emergency_compress
        agent4 = Agent(
            config=AgentConfig(workspace_dir=workspace, max_iterations=4),
            llm=MockLLM(token_limit=500),
            tools=_make_tools(),
            session_mgr=mgr4,
            summarizer=Summarizer(max_tokens=8000),
            context_builder=ContextBuilder(workspace),
        )

        for i in range(3):
            msg = f"Chat #{i+1}: " + ("Z" * 200)
            print(f">>> [USER]: {msg[:40]}...")
            r = agent4.run(msg)
            print(f"<<< [AGENT]: {r}")
            print(f"    [Prompt size: {len(agent4.prompt.messages)} messages]\n")


if __name__ == "__main__":
    main()
