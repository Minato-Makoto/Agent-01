import json
import logging
import tempfile
import sys
from pathlib import Path
from agentforge.agent_core import Agent, AgentConfig, StreamCallbacks
from agentforge.contracts import ChatCompletionResult, ToolCall, ProviderCapabilities
from agentforge.summarizer import Summarizer
from agentforge.tools import ToolRegistry, Tool, ToolResult
from agentforge.context import ContextBuilder
from agentforge.session import SessionManager

logging.getLogger("agentforge").setLevel(logging.ERROR)

class MockLLM:
    def __init__(self):
        self.capabilities = ProviderCapabilities(supports_tools=True)
        self.turn = 1

    def chat_completion(self, messages, tools=None, **kwargs):
        print(f"\n================ [LLM CALL {self.turn}] MÔ HÌNH THỰC TẾ NHẬN ĐƯỢC Payload =================")
        clean_msgs = []
        for m in messages:
            clean_msgs.append({k: v for k, v in m.items() if v})
        print(json.dumps(clean_msgs, indent=2, ensure_ascii=False))
        print("========================================================================================\n")
        
        # Fake a hard API API Limit constraint
        total_len = sum(len(str(m)) for m in messages)
        if total_len > 3800:
            print(f"!!! [API SERVER TỪ CHỐI] Báo lỗi 'Token Limit Exceeded' vì tổng ký tự = {total_len} > Mức cho phép 3800 !!!\n")
            return ChatCompletionResult(content="", error="Token Limit Exceeded")

        res_map = {
            1: ChatCompletionResult(content="Chào bạn!"),
            2: ChatCompletionResult(content="Mình đã nhớ cục văn bản lớn này."),
            3: ChatCompletionResult(
                content="Đang đọc file...",
                tool_calls=[ToolCall(id="call_123", name="dummy_read_file", arguments={"path": "config.json"})]
            ),
            4: ChatCompletionResult(content="Tôi đã đọc xong file, nội dung chủ yếu là các chữ A hahaha!"),
            5: ChatCompletionResult(content="Ok, mình hiểu rồi, có cần đọc file khác không?"),
            6: ChatCompletionResult(content="Tạm biệt!")
        }

        res = res_map.get(self.turn, ChatCompletionResult(content="Hoàn tất."))
        self.turn += 1
        return res

def main():
    # Force stdout to process utf-8 to avoid Windows charmap errors
    sys.stdout.reconfigure(encoding='utf-8')
    
    root_dir = Path(__file__).parent
    workspace_dir = root_dir / "workspace"
    
    tools = ToolRegistry()
    def dummy_read(args):
        return ToolResult(success=True, output="[NỘI DUNG FILE]\nDAU_FILE\n" + ("A"*2500) + "\nCUOI_FILE")
    
    tools.register(Tool(
        name="dummy_read_file", 
        description="Đọc file", 
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        execute_fn=dummy_read
    ))
    
    summarizer = Summarizer(max_tokens=6000, chars_per_token=4) 
    
    with tempfile.TemporaryDirectory() as temp_dir:
        context_builder = ContextBuilder(workspace_dir=str(workspace_dir))
        session_mgr = SessionManager(sessions_dir=temp_dir)
        session_mgr.new_session()
        
        config = AgentConfig(name="SimAgent", max_iterations=4)
        llm = MockLLM()
        
        agent = Agent(
            config=config,
            llm=llm,
            tools=tools,
            session_mgr=session_mgr,
            summarizer=summarizer,
            context_builder=context_builder
        )
        
        agent._update_system_prompt()

        cb = StreamCallbacks()
        
        print(">>> [NGƯỜI DÙNG]: Xin chào")
        agent.run("Xin chào", cb)
        
        print("\n\n>>> [NGƯỜI DÙNG]: Gửi 1 block text cực lớn (1500 ký tự)")
        agent.run("Nhớ đoạn text này nhé: " + ("B" * 1500), cb)
        
        print("\n\n>>> [NGƯỜI DÙNG]: Đọc file config.json (Tool sẽ nhả ra 2500 ký tự)")
        agent.run("Đọc file config.json nhé", cb)

        print("\n\n>>> [NGƯỜI DÙNG]: Giờ chat tiếp bình thường (Kích hoạt TIER 1 - GRACEFUL SUMMARIZE)")
        agent.run("Ok, cảm ơn bạn", cb)

if __name__ == "__main__":
    main()
