"""
AgentForge — Context Window Summarizer.

3-tier compression (PicoClaw loop.go + OpenClaw pruner.ts):
1. Soft trim: Prune long tool results (keep head/tail, replace middle)
2. Graceful summarization: LLM-based summary of old messages
3. Emergency compression: aggressive truncation when context overflows
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Summarizer:
    """Manages context window compression via summarization."""

    def __init__(self, max_tokens: int = 8192, chars_per_token: int = 4):
        self._max_tokens = max_tokens
        self._chars_per_token = chars_per_token
        self._soft_trim_threshold = 0.6   # prune tool results at 60%
        self._summary_threshold = 0.7     # summarize at 70% capacity
        # Max length for a single tool result before pruning
        self._max_tool_result_chars = 2000

    @property
    def max_chars(self) -> int:
        return self._max_tokens * self._chars_per_token

    @property
    def threshold_chars(self) -> int:
        return int(self.max_chars * self._summary_threshold)

    @property
    def soft_trim_chars(self) -> int:
        return int(self.max_chars * self._soft_trim_threshold)

    def estimate_tokens(self, messages: List[Dict[str, Any]], system_prompt: str = "") -> int:
        """Estimate total token count for messages + system prompt."""
        total_chars = len(system_prompt)
        for msg in messages:
            total_chars += len(str(msg.get("content", ""))) + len(msg.get("role", "")) + 20
            if msg.get("tool_calls"):
                total_chars += len(json.dumps(msg["tool_calls"]))
        return total_chars // self._chars_per_token

    def needs_summarization(self, messages: List[Dict[str, Any]], system_prompt: str = "") -> bool:
        """Check if messages exceed the summarization threshold."""
        total_chars = len(system_prompt)
        for msg in messages:
            total_chars += len(str(msg.get("content", ""))) + len(msg.get("role", "")) + 20
            if msg.get("tool_calls"):
                total_chars += len(json.dumps(msg["tool_calls"]))
        return total_chars > self.threshold_chars

    def prune_tool_results(self, messages: List[Dict[str, Any]], system_prompt: str = "") -> List[Dict[str, Any]]:
        """
        Tier 0.5: Soft trim — prune long tool results in-place.
        
        When total context exceeds soft_trim_threshold, replace long tool
        outputs with head/tail excerpts. Preserves recent messages.
        Pattern: OpenClaw pruner.ts soft-trim.
        """
        total_chars = len(system_prompt)
        for msg in messages:
            total_chars += len(str(msg.get("content", ""))) + 20
            if msg.get("tool_calls"):
                total_chars += len(json.dumps(msg["tool_calls"]))

        if total_chars < self.soft_trim_chars:
            return messages  # No pruning needed

        # Prune ALL long tool results (LLM already saw full output)
        pruned = []
        for msg in messages:
            if msg.get("role") == "tool" and len(str(msg.get("content", ""))) > self._max_tool_result_chars:
                # Truncate: keep first 500 + last 500 chars
                content = str(msg.get("content", ""))
                head = content[:500]
                tail = content[-500:]
                trimmed_content = f"{head}\n\n[... {len(content) - 1000} chars pruned ...]\n\n{tail}"
                pruned.append({**msg, "content": trimmed_content})
            else:
                pruned.append(msg)

        return pruned

    def graceful_summarize(
        self,
        messages: List[Dict[str, Any]],
        existing_summary: str,
        llm_fn: Optional[Callable] = None,
    ) -> tuple:
        """
        Tier 1: Graceful summarization.
        
        Keeps recent messages, compresses older ones into a summary.
        If llm_fn is provided, uses it to generate the summary.
        Otherwise, does a simple text-based compression.
        
        Returns: (summary_text, remaining_messages)
        """
        if len(messages) < 6:
            return existing_summary, messages

        # Keep the most recent 4 messages (2 user-assistant pairs)
        keep_count = 4
        old_messages = messages[:-keep_count]
        recent_messages = messages[-keep_count:]

        # Build summary text from old messages
        old_text = self._messages_to_text(old_messages)

        if llm_fn:
            # Use LLM to generate a concise summary
            prompt = f"""Summarize this conversation history concisely. Keep key facts, decisions, and context.

Previous summary: {existing_summary or '(none)'}

New messages to summarize:
{old_text}

Write a concise summary (max 200 words):"""
            try:
                summary = llm_fn(prompt)
                if summary:
                    return summary.strip(), recent_messages
            except Exception as exc:
                logger.warning("LLM summarization failed; falling back to local summary: %s", exc)

        # Fallback: simple text concatenation
        parts = []
        if existing_summary:
            parts.append(existing_summary)
        parts.append(f"[Compressed {len(old_messages)} messages]")

        # Extract key content from old messages
        for msg in old_messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            if content.strip():
                parts.append(f"- {role}: {content}")

        summary = "\n".join(parts)
        return summary, recent_messages

    def emergency_compress(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tier 2: Emergency compression.
        
        Aggressively removes old messages to fit within context window.
        Keeps only the 2 most recent messages.
        Pattern: PicoClaw loop.go:forceCompression (drop oldest 50%).
        """
        if len(messages) <= 2:
            return messages

        # Keep only the last 2 messages
        return messages[-2:]

    def _messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """Convert messages to readable text for summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            if content.strip():
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

