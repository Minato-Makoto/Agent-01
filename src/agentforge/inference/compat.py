from __future__ import annotations

from typing import Any, Dict, Tuple

from ..contracts import ProviderCapabilities


class CompatFallback:
    """Compatibility fallback ladder for provider-specific payload errors."""

    def __init__(
        self,
        *,
        unsupported_error_keywords: Tuple[str, ...],
        capabilities: ProviderCapabilities,
    ):
        self._unsupported_error_keywords = unsupported_error_keywords
        self._capabilities = capabilities

    def update_keywords(self, keywords: Tuple[str, ...]) -> None:
        self._unsupported_error_keywords = keywords

    def update_capabilities(self, capabilities: ProviderCapabilities) -> None:
        self._capabilities = capabilities

    def is_unsupported_param_error(self, error_text: str, *params: str) -> bool:
        msg = (error_text or "").lower()
        if not msg:
            return False
        if not any((p or "").lower() in msg for p in params):
            return False
        return any(k in msg for k in self._unsupported_error_keywords)

    def is_tools_unsupported_error(self, error_text: str) -> bool:
        return self.is_unsupported_param_error(error_text, "tools", "tool_choice")

    def apply_payload_fallback(
        self,
        payload: Dict[str, Any],
        error_text: str,
    ) -> Tuple[bool, bool]:
        """
        Try to remove unsupported optional params and retry.

        Returns:
            (changed_payload, used_tools_fallback)
        """
        used_tools_fallback = False

        if ("tools" in payload or "tool_choice" in payload) and self.is_tools_unsupported_error(
            error_text
        ):
            self._capabilities.supports_tools = False
            self._capabilities.supports_parallel_tool_calls = False
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            payload.pop("parallel_tool_calls", None)
            return True, True

        if ("parallel_tool_calls" in payload) and self.is_unsupported_param_error(
            error_text, "parallel_tool_calls"
        ):
            self._capabilities.supports_parallel_tool_calls = False
            payload.pop("parallel_tool_calls", None)
            return True, used_tools_fallback

        if ("response_format" in payload) and self.is_unsupported_param_error(
            error_text, "response_format"
        ):
            self._capabilities.supports_response_format = False
            payload.pop("response_format", None)
            return True, used_tools_fallback

        if ("max_completion_tokens" in payload) and self.is_unsupported_param_error(
            error_text, "max_completion_tokens"
        ):
            payload["max_tokens"] = payload.pop("max_completion_tokens")
            return True, used_tools_fallback

        if ("max_tokens" in payload) and self.is_unsupported_param_error(error_text, "max_tokens"):
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            return True, used_tools_fallback

        if ("reasoning_effort" in payload) and self.is_unsupported_param_error(
            error_text, "reasoning_effort"
        ):
            self._capabilities.supports_reasoning_effort = False
            payload.pop("reasoning_effort", None)
            return True, used_tools_fallback

        if ("reasoning_format" in payload) and self.is_unsupported_param_error(
            error_text, "reasoning_format"
        ):
            self._capabilities.supports_reasoning_format = False
            payload.pop("reasoning_format", None)
            return True, used_tools_fallback

        if ("stream" in payload) and self.is_unsupported_param_error(error_text, "stream"):
            self._capabilities.supports_stream = False
            payload.pop("stream", None)
            return True, used_tools_fallback

        if ("grammar" in payload) and self.is_unsupported_param_error(error_text, "grammar"):
            payload.pop("grammar", None)
            return True, used_tools_fallback

        if ("stop" in payload) and self.is_unsupported_param_error(error_text, "stop"):
            payload.pop("stop", None)
            return True, used_tools_fallback

        return False, used_tools_fallback

