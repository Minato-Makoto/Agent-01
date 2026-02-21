"""
AgentForge — agent runtime loop.

Design goals:
- Structured tool-calling first (OpenAI-compatible `tool_calls`)
- Text parser fallback for providers that emit textual tool payloads
- Stable callback and session behavior across local and remote backends
"""

from __future__ import annotations

import importlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .context import ContextBuilder
from .contracts import ChatCompletionResult, ToolCall
from .llm_inference import LLMInference
from .prompting import ChatMessage, PromptBuilder
from .session import SessionManager
from .skills import SkillInfo, SkillLoader
from .summarizer import Summarizer
from .tool_call_parser import ToolCallParser
from .tool_loop import ToolLoop
from .tool_mutation import is_mutating_tool_call
from .tools import Tool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configurable runtime limits and behavior flags."""

    name: str = ""
    workspace_dir: str = ""
    max_iterations: int = 10
    max_repeats: int = 3
    timeout: float = 300.0
    verbose: bool = False
    parallel_tool_calls: bool = False


OutputCallback = Callable[[str], None]


@dataclass
class StreamCallbacks:
    """Runtime callbacks used by CLI/UI integration."""

    on_token: Optional[OutputCallback] = None
    on_reasoning: Optional[OutputCallback] = None
    on_tool_call: Optional[Callable[[str, Dict], None]] = None
    on_tool_call_start: Optional[Callable[[str, int], None]] = None
    on_tool_call_delta: Optional[Callable[[int, str], None]] = None
    on_tool_call_end: Optional[Callable[[int], None]] = None
    on_tool_result: Optional[Callable[[str, Any], None]] = None
    on_stream_start: Optional[Callable[[], None]] = None
    on_stream_end: Optional[Callable[[], None]] = None
    on_thinking_start: Optional[Callable[[], None]] = None
    on_thinking_end: Optional[Callable[[], None]] = None
    on_skill_activated: Optional[Callable[[str], None]] = None


class Agent:
    """Main orchestration loop for tool -> answer cycles."""

    _DEFAULT_STOP: List[str] = ["<|im_end|>", "<|end|>", "</s>", "<|eot_id|>"]

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMInference,
        tools: ToolRegistry,
        session_mgr: Optional[SessionManager] = None,
        summarizer: Optional[Summarizer] = None,
        skill_loader: Optional[SkillLoader] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.config = config
        self.llm = llm
        self.tools = tools

        self.prompt = PromptBuilder()
        self.parser = ToolCallParser()
        self.tool_loop = ToolLoop(
            registry=tools,
            max_iterations=config.max_iterations,
            max_repeats=config.max_repeats,
            timeout=config.timeout,
        )

        self.session_mgr = session_mgr
        self.summarizer = summarizer
        self.skill_loader = skill_loader
        self.context_builder = context_builder

        self._register_bootstrap_tools()
        self._update_system_prompt()
        if self.session_mgr and self.session_mgr.session and self.session_mgr.session.messages:
            self._hydrate_prompt_from_session()

    def reset(self) -> None:
        """Reset transient prompt/tool-loop state."""
        self.prompt.clear()
        self.tool_loop.reset()

    def _hydrate_prompt_from_session(self) -> None:
        """Hydrate runtime prompt history from persisted session transcript."""
        if not self.session_mgr or not self.session_mgr.session:
            return
        self.prompt.clear()
        for msg in self.session_mgr.session.messages:
            self.prompt.messages.append(
                ChatMessage(
                    role=msg.role,
                    content=msg.content,
                    tool_call_id=msg.tool_call_id,
                    tool_calls=msg.tool_calls,
                    tool_name=msg.tool_name,
                )
            )

    def run(self, user_input: str, callbacks: Optional[StreamCallbacks] = None) -> str:
        """Execute one user turn and return the final assistant text."""
        cb = callbacks or StreamCallbacks()

        self.prompt.add_user(user_input)
        if self.session_mgr:
            self.session_mgr.add_message("user", user_input)

        self._maybe_summarize_prompt_history()

        self.tool_loop.reset()
        start_time = time.time()

        for iteration in range(self.config.max_iterations):
            can_continue, reason = self.tool_loop.should_continue(iteration, start_time)
            if not can_continue:
                logger.warning("Tool loop stopped: %s", reason)
                return f"[Agent stopped: {reason}]"

            result = self._run_model_once(cb)
            if result.error:
                if self._try_emergency_context_compress(result.error):
                    continue
                return f"[LLM Error: {result.error}]"

            tool_calls = self._resolve_tool_calls(result)
            if tool_calls:
                self._append_assistant_tool_calls(tool_calls, result.content or "")
                self._execute_tool_calls(
                    tool_calls,
                    cb,
                    tool_calls_streamed=bool(result.tool_calls_streamed),
                )
                continue

            answer = (result.content or "").strip()
            self.prompt.add_assistant(answer)
            if self.session_mgr:
                self.session_mgr.add_message("assistant", answer)
            return answer

        return f"[Agent reached max iterations ({self.config.max_iterations})]"

    def _run_model_once(self, cb: StreamCallbacks) -> ChatCompletionResult:
        messages = self._build_messages()
        provider_tools = self.tools.to_openai_tools()

        self._safe_callback(cb.on_thinking_start, "on_thinking_start")
        try:
            result = self.llm.chat_completion(
                messages=messages,
                tools=provider_tools,
                tool_choice="auto",
                parallel_tool_calls=self.config.parallel_tool_calls,
                stop=self._DEFAULT_STOP,
                on_token=cb.on_token,
                on_reasoning=cb.on_reasoning,
                on_tool_call_start=cb.on_tool_call_start,
                on_tool_call_delta=cb.on_tool_call_delta,
                on_tool_call_end=cb.on_tool_call_end,
            )
        finally:
            self._safe_callback(cb.on_thinking_end, "on_thinking_end")
            # Stream start remains a UI concern; stream_end is still emitted here
            # to preserve current behavior across agent iterations.
            self._safe_callback(cb.on_stream_end, "on_stream_end")
        return result

    def _append_assistant_tool_calls(self, tool_calls: List[ToolCall], content: str) -> None:
        self.prompt.add_assistant_tool_calls(tool_calls, content=content)
        if not self.session_mgr:
            return
        self.session_mgr.add_assistant_tool_calls(
            [tc.to_openai_message_tool_call() for tc in tool_calls],
            content=content,
        )

    def _execute_tool_calls(
        self,
        tool_calls: List[ToolCall],
        cb: StreamCallbacks,
        *,
        tool_calls_streamed: bool = False,
    ) -> None:
        for tc in tool_calls:
            if not tool_calls_streamed:
                self._safe_callback(cb.on_tool_call, "on_tool_call", tc.name, tc.arguments)

            tool_result = self.tool_loop.execute_tool(tc.name, tc.arguments, tc.id)
            llm_result_text = tool_result.to_string()

            self.prompt.add_tool_result(tc.id, tc.name, llm_result_text)
            if self.session_mgr:
                self.session_mgr.add_tool_result(tc.id, tc.name, llm_result_text)

            if cb.on_tool_result:
                self._emit_tool_result_to_callback(tc, tool_result, cb)

            if tc.name == "read_file":
                self._emit_skill_activation_if_needed(tc, cb)

    def _emit_tool_result_to_callback(
        self,
        tool_call: ToolCall,
        tool_result: ToolResult,
        cb: StreamCallbacks,
    ) -> None:
        mutating = is_mutating_tool_call(tool_call.name, tool_call.arguments)
        if not tool_result.success and not mutating and not self.config.verbose:
            logger.warning(
                "Suppressed non-mutating tool failure from user output: %s",
                tool_result.error,
            )
            return

        display = (
            tool_result.for_user
            if (tool_result.for_user and not tool_result.silent)
            else tool_result.to_string()
        )
        self._safe_callback(cb.on_tool_result, "on_tool_result", tool_call.name, display)

    def _emit_skill_activation_if_needed(self, tool_call: ToolCall, cb: StreamCallbacks) -> None:
        if not cb.on_skill_activated or not self.skill_loader:
            return
        skill_path = str(tool_call.arguments.get("path", ""))
        if not skill_path:
            return
        skill = self.skill_loader.find_skill_by_file(skill_path)
        if skill and skill.active:
            self._safe_callback(cb.on_skill_activated, "on_skill_activated", skill.name)

    def _try_emergency_context_compress(self, error_message: str) -> bool:
        if not self.summarizer:
            return False
        lowered = (error_message or "").lower()
        if not any(token in lowered for token in ("token", "context", "length")):
            return False

        logger.warning("Context overflow detected. Triggering emergency compression.")
        messages_dicts = [{"role": m.role, "content": m.content} for m in self.prompt.messages]
        remaining = self.summarizer.emergency_compress(messages_dicts)
        self.prompt.clear()
        for msg in remaining:
            self.prompt.messages.append(
                ChatMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            )
        return True

    def _maybe_summarize_prompt_history(self) -> None:
        if not self.summarizer:
            return

        message_dicts = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "tool_name": msg.tool_name,
            }
            for msg in self.prompt.messages
        ]
        message_dicts = self.summarizer.prune_tool_results(
            message_dicts,
            self.prompt.system_message,
        )
        if not self.summarizer.needs_summarization(message_dicts, self.prompt.system_message):
            return

        existing_summary = ""
        if self.session_mgr and self.session_mgr.session:
            existing_summary = self.session_mgr.session.summary

        def _llm_summary_fn(summary_prompt: str) -> str:
            generated = (self.llm.generate(prompt=summary_prompt, max_tokens=768) or "").strip()
            if not generated or generated.startswith("[Error:"):
                raise RuntimeError("llm summary generation failed")
            return generated

        summary, remaining = self.summarizer.graceful_summarize(
            message_dicts,
            existing_summary,
            llm_fn=_llm_summary_fn,
        )
        did_compress = len(remaining) < len(message_dicts)
        if self.session_mgr and self.session_mgr.session:
            old_session_id = self.session_mgr.session.id
            self.session_mgr.set_summary(summary)
            if did_compress:
                try:
                    self.session_mgr.branch_session(
                        summary=summary,
                        old_id=old_session_id,
                        continuation_messages=remaining,
                    )
                    self._hydrate_prompt_from_session()
                    return
                except Exception:
                    logger.exception("Session branching failed; falling back to in-memory summary mode.")

        self.prompt.clear()
        if summary:
            self.prompt.add_user(f"[Previous conversation summary: {summary}]")
            self.prompt.add_assistant(
                "Understood. I have the context from our previous conversation."
            )
        for msg in remaining:
            self.prompt.messages.append(
                ChatMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    tool_call_id=msg.get("tool_call_id", ""),
                    tool_calls=msg.get("tool_calls"),
                    tool_name=msg.get("tool_name", ""),
                )
            )

    def _resolve_tool_calls(self, result: ChatCompletionResult) -> List[ToolCall]:
        tool_calls = list(result.tool_calls or [])
        if tool_calls:
            return tool_calls

        if self._should_try_fallback_parser(
            result_content=result.content,
            used_tools_fallback=result.used_tools_fallback,
        ):
            return self._fallback_parse_tool_calls(result.content)
        return []

    def _fallback_parse_tool_calls(self, raw_text: str) -> List[ToolCall]:
        parsed = self.parser.parse(raw_text or "")
        if not parsed.has_tool_calls:
            return []

        logger.info("Compatibility fallback: parsed tool calls from plain text response.")
        return [ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments) for tc in parsed.tool_calls]

    def _should_try_fallback_parser(self, result_content: str, used_tools_fallback: bool) -> bool:
        """
        Enable textual tool-call parser in compatibility scenarios.

        Primary trigger is endpoint capability detection. We also keep a known
        marker heuristic for providers that advertise tools but emit tool text.
        """
        if getattr(self.llm.capabilities, "supports_tools", None) is False:
            return True
        if used_tools_fallback:
            return True

        text = (result_content or "").strip()
        if not text:
            return False
        markers = ("<tool_call>", "</tool_call>", '"tool":', '"name":', "<arguments>")
        return any(marker in text for marker in markers)

    def _safe_callback(self, callback: Optional[Callable[..., Any]], name: str, *args: Any) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            logger.exception("Callback '%s' raised and was ignored.", name)

    def _register_bootstrap_tools(self) -> None:
        def read_file_fn(args: Dict[str, Any]) -> ToolResult:
            raw_path = str(args.get("path", "")).strip()
            if not raw_path:
                return ToolResult.error_result("Missing 'path' parameter")
            if not os.path.exists(raw_path):
                return ToolResult.error_result(f"File not found: {raw_path}")

            try:
                with open(raw_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                return ToolResult.error_result(str(exc))

            if self.skill_loader:
                skill = self.skill_loader.find_skill_by_file(raw_path)
                if skill and not skill.active:
                    self._activate_skill(skill)

            return ToolResult(success=True, output=content)

        self.tools.register(
            Tool(
                name="read_file",
                description="Read file contents. Reading a SKILL_xxx.md file activates that skill.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute path to the file.",
                        }
                    },
                    "required": ["path"],
                },
                execute_fn=read_file_fn,
            )
        )

    def _activate_skill(self, skill: SkillInfo) -> None:
        if not self.skill_loader:
            return
        self.skill_loader.activate(skill.name)

        if not skill.module:
            logger.warning("Skill '%s' has no module in frontmatter; skipping tool load.", skill.name)
            self._update_system_prompt()
            return

        try:
            module = importlib.import_module(skill.module)
            if hasattr(module, "register"):
                module.register(self.tools, skill.name)
                logger.info("Skill activated: %s", skill.name)
        except ImportError as exc:
            logger.warning("Could not load tools for skill '%s': %s", skill.name, exc)
        except Exception as exc:
            logger.exception("Error activating skill '%s': %s", skill.name, exc)

        self._update_system_prompt()

    def _update_system_prompt(self) -> None:
        if not self.context_builder:
            self.prompt.set_system("You are a helpful assistant.")
            return

        skills_xml = self.skill_loader.build_skills_xml() if self.skill_loader else ""
        tool_summaries = []
        for tool in self.tools.get_all():
            first_sentence = tool.description.split(".")[0].strip()
            tool_summaries.append((tool.name, first_sentence))

        system_prompt = self.context_builder.build_system_prompt(
            skills_xml=skills_xml,
            tool_summaries=tool_summaries,
        )
        self.prompt.set_system(system_prompt)

    def _build_messages(self) -> List[Dict[str, Any]]:
        return self.prompt.build_messages(include_system=True)
