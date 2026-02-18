"""
AgentForge — LLM inference transport.

Supports:
- Local llama-server process mode
- Remote OpenAI-compatible endpoint mode
- Structured tool-calling with runtime capability fallback
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .contracts import ChatCompletionResult, ProviderCapabilities, ToolCall
from .inference.compat import CompatFallback
from .inference.http_transport import HttpTransport
from .inference.server_manager import LocalServerManager
from .schema_normalizer import normalize_openai_tools_for_provider
from .tool_id import sanitize_tool_call_id
from .transcript_policy import (
    apply_transcript_policy,
    detect_provider_kind,
    resolve_transcript_policy,
)

logger = logging.getLogger(__name__)


@dataclass
class InferenceConfig:
    """Configuration for LLM inference."""

    n_ctx: int = 8192
    n_gpu_layers: int = -1
    n_threads: int = 0
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 4096
    seed: int = -1
    repeat_penalty: float = 1.1
    host: str = "127.0.0.1"
    port: int = 8080
    model_id: str = "local"
    boot_timeout_s: int = 120
    health_timeout_s: int = 2
    request_timeout_s: int = 300
    health_path: str = "/health"
    local_chat_endpoint: str = "/v1/chat/completions"
    local_completion_endpoint: str = "/completion"
    remote_chat_endpoint: str = "/v1/chat/completions"
    remote_completion_endpoint: str = "/v1/completions"
    # Non-standard provider extension used by llama.cpp-style servers.
    reasoning_format: str = "auto"
    # OpenAI Chat Completions parameter for reasoning models.
    reasoning_effort: str = ""
    tools_probe_user_prompt: str = "ping"
    tools_probe_tool_name: str = "probe_noop"
    tools_probe_description: str = "probe"
    tools_probe_max_tokens: int = 1
    health_poll_interval_s: float = 1.0
    compat_retry_limit: int = 8
    max_requests_per_minute: int = 60
    http_error_body_chars: int = 1200
    sse_data_prefix: str = "data: "
    sse_done_marker: str = "[DONE]"
    unsupported_error_keywords: Tuple[str, ...] = (
        "unsupported",
        "not supported",
        "not compatible",
        "unknown field",
        "unknown parameter",
        "invalid param",
        "unrecognized",
        "extra inputs are not permitted",
        "not allowed",
        "unexpected keyword",
    )


class LLMInference:
    """Manages LLM endpoint and chat-completion requests."""

    def __init__(self):
        self._config = InferenceConfig()
        self._loaded = False
        self._mode = "local"  # local | remote
        self._model_path = ""
        self._server_exe = ""
        self._base_url = ""
        self._chat_endpoint = self._config.local_chat_endpoint
        self._completion_endpoint = self._config.local_completion_endpoint
        self._api_key = ""
        self._capabilities = ProviderCapabilities()
        self._provider_kind = "llama_cpp"

        self._server = LocalServerManager()
        self._transport = HttpTransport()
        self._compat = CompatFallback(
            unsupported_error_keywords=self._config.unsupported_error_keywords,
            capabilities=self._capabilities,
        )
        # Backward-compatible attribute for callers/tests that may inspect process state.
        self._server_process = None
        self._refresh_runtime_helpers()

    def _set_config(self, config: InferenceConfig) -> None:
        self._config = config
        self._refresh_runtime_helpers()

    def _reset_capabilities(self) -> None:
        self._capabilities = ProviderCapabilities()
        self._compat.update_capabilities(self._capabilities)

    def _refresh_runtime_helpers(self) -> None:
        self._compat.update_keywords(self._config.unsupported_error_keywords)
        self._compat.update_capabilities(self._capabilities)
        self._transport.configure(
            base_url=self._base_url,
            api_key=self._api_key,
            request_timeout_s=self._config.request_timeout_s,
            http_error_body_chars=self._config.http_error_body_chars,
            max_requests_per_minute=self._config.max_requests_per_minute,
        )

    def load_model(
        self, model_path: str, config: Optional[InferenceConfig] = None, server_exe: str = ""
    ) -> bool:
        """Start local llama-server with the given model."""
        if config:
            self._set_config(config)

        self._mode = "local"
        self._model_path = model_path
        self._server_exe = server_exe
        self._base_url = f"http://{self._config.host}:{self._config.port}"
        self._chat_endpoint = self._config.local_chat_endpoint
        self._completion_endpoint = self._config.local_completion_endpoint
        self._api_key = ""
        self._reset_capabilities()
        self._provider_kind = "llama_cpp"
        self._refresh_runtime_helpers()

        if not server_exe or not os.path.exists(server_exe):
            logger.error("[LLM] llama-server.exe not found: %s", server_exe)
            return False
        if not model_path or not os.path.exists(model_path):
            logger.error("[LLM] Model file not found: %s", model_path)
            return False

        logger.info("[LLM] Starting llama-server...")
        logger.info("[LLM] Model: %s", os.path.basename(model_path))
        started = self._server.start(
            server_exe=server_exe,
            model_path=model_path,
            host=self._config.host,
            port=self._config.port,
            n_ctx=self._config.n_ctx,
            n_gpu_layers=self._config.n_gpu_layers,
            n_threads=self._config.n_threads,
            base_url=self._base_url,
            health_path=self._config.health_path,
            health_timeout_s=self._config.health_timeout_s,
            health_poll_interval_s=self._config.health_poll_interval_s,
            boot_timeout_s=self._config.boot_timeout_s,
        )
        self._server_process = self._server.process
        if not started:
            logger.error("[LLM] Server failed to start within timeout.")
            self.unload()
            return False

        self._loaded = True
        logger.info("[LLM] Server ready at %s", self._base_url)
        return True

    def connect_remote(
        self, base_url: str, model_id: str, api_key: str = "", config: Optional[InferenceConfig] = None
    ) -> bool:
        """Attach to a remote OpenAI-compatible endpoint (no local process)."""
        if config:
            self._set_config(config)
        if not base_url:
            logger.error("[LLM] base_url is required for remote mode.")
            return False

        self._mode = "remote"
        self._model_path = ""
        self._server_exe = ""
        self._server_process = None
        self._api_key = api_key or ""
        self._config.model_id = model_id or "local"
        self._base_url = base_url.rstrip("/")
        self._reset_capabilities()
        self._provider_kind = detect_provider_kind(
            mode="remote", base_url=self._base_url, model_id=self._config.model_id
        )

        if self._base_url.endswith("/v1"):
            self._chat_endpoint = "/chat/completions"
            self._completion_endpoint = "/completions"
        else:
            self._chat_endpoint = self._config.remote_chat_endpoint
            self._completion_endpoint = self._config.remote_completion_endpoint

        self._refresh_runtime_helpers()
        self._loaded = True
        logger.info("[LLM] Remote endpoint ready: %s", self._base_url)
        return True

    def unload(self):
        """Stop local server process (if any)."""
        self._server.stop()
        self._server_process = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_desc(self) -> str:
        if self._mode == "remote":
            return self._config.model_id
        if not self._model_path:
            return ""
        return os.path.basename(self._model_path)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def generate(
        self,
        prompt: str,
        grammar: str = "",
        stop: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using completion endpoint (mainly local compatibility)."""
        if not self._loaded:
            return "[Error: Server not running]"

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": max_tokens or self._config.max_tokens,
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
        }
        if stop:
            payload["stop"] = stop
        if grammar:
            payload["grammar"] = grammar
        if self._config.seed >= 0:
            payload["seed"] = self._config.seed

        try:
            resp = self._post(self._completion_endpoint, payload)
            if "content" in resp:
                return str(resp["content"])
            choices = resp.get("choices", [])
            if choices:
                return str(choices[0].get("text", ""))
            return ""
        except Exception as exc:
            return f"[Error: {exc}]"

    def _is_unsupported_param_error(self, error_text: str, *params: str) -> bool:
        return self._compat.is_unsupported_param_error(error_text, *params)

    def _is_tools_unsupported_error(self, error_text: str) -> bool:
        return self._compat.is_tools_unsupported_error(error_text)

    def _should_send_reasoning_format(self) -> bool:
        if self._capabilities.supports_reasoning_format is False:
            return False
        if not self._config.reasoning_format:
            return False
        return self._provider_kind not in {"openai", "openrouter", "anthropic", "gemini"}

    def _should_send_reasoning_effort(self) -> bool:
        if self._capabilities.supports_reasoning_effort is False:
            return False
        if not self._config.reasoning_effort:
            return False
        return self._provider_kind in {"openai", "openrouter", "openai_compatible"}

    def _resolved_model_id(self) -> str:
        model = (self._config.model_id or "").strip().lower()
        if "/" in model:
            model = model.rsplit("/", 1)[-1]
        return model

    def _should_prefer_max_completion_tokens(self) -> bool:
        if self._provider_kind not in {"openai", "openrouter", "openai_compatible"}:
            return False
        return bool(re.match(r"^o\d", self._resolved_model_id()))

    def _apply_chat_token_limit(self, payload: Dict[str, Any], max_tokens: Optional[int]) -> None:
        limit = max_tokens if max_tokens is not None else self._config.max_tokens
        if self._should_prefer_max_completion_tokens():
            payload["max_completion_tokens"] = limit
            payload.pop("max_tokens", None)
            return
        payload["max_tokens"] = limit
        payload.pop("max_completion_tokens", None)

    def _apply_compat_payload_fallback(
        self, payload: Dict[str, Any], error_text: str
    ) -> Tuple[bool, bool]:
        return self._compat.apply_payload_fallback(payload, error_text)

    def _post_with_compat_fallback(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        used_tools_fallback = False
        for _ in range(max(1, self._config.compat_retry_limit)):
            try:
                return self._post(endpoint, payload), used_tools_fallback
            except Exception as exc:
                changed, used_tools = self._apply_compat_payload_fallback(payload, str(exc))
                used_tools_fallback = used_tools_fallback or used_tools
                if changed:
                    continue
                raise
        raise RuntimeError("Provider compatibility retry limit reached.")

    def _probe_supports_tools(self, messages: List[Dict[str, Any]]) -> bool:
        if self._capabilities.supports_tools is not None:
            return bool(self._capabilities.supports_tools)

        transcript_policy = resolve_transcript_policy(
            provider=self._provider_kind, model_id=self._config.model_id
        )
        sanitized_messages, _ = apply_transcript_policy(messages, transcript_policy)
        probe_source_messages = sanitized_messages or messages
        probe_messages = (
            probe_source_messages[-2:]
            if probe_source_messages
            else [{"role": "user", "content": self._config.tools_probe_user_prompt}]
        )
        probe_payload = {
            "model": self._config.model_id,
            "messages": probe_messages,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": self._config.tools_probe_tool_name,
                        "description": self._config.tools_probe_description,
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "tool_choice": "auto",
        }
        self._apply_chat_token_limit(probe_payload, self._config.tools_probe_max_tokens)
        try:
            self._post(self._chat_endpoint, probe_payload)
            self._capabilities.supports_tools = True
        except Exception as exc:
            if self._is_tools_unsupported_error(str(exc)):
                self._capabilities.supports_tools = False
            else:
                self._capabilities.supports_tools = True
        return bool(self._capabilities.supports_tools)

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        parallel_tool_calls: bool = False,
        response_format: Optional[Dict[str, Any]] = None,
        grammar: str = "",
        stop: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        on_token=None,
        on_reasoning=None,
    ) -> ChatCompletionResult:
        """Generate from chat-completions endpoint."""
        if not self._loaded:
            return ChatCompletionResult(error="Server not running")

        transcript_policy = resolve_transcript_policy(
            provider=self._provider_kind, model_id=self._config.model_id
        )
        policy_messages, _ = apply_transcript_policy(messages, transcript_policy)
        effective_messages = policy_messages or messages
        can_use_tools = bool(tools) and self._probe_supports_tools(effective_messages)
        provider_tools = (
            normalize_openai_tools_for_provider(tools or [], self._provider_kind) if tools else []
        )

        payload: Dict[str, Any] = {
            "model": self._config.model_id,
            "messages": effective_messages,
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
        }
        self._apply_chat_token_limit(payload, max_tokens)
        if self._should_send_reasoning_effort():
            payload["reasoning_effort"] = self._config.reasoning_effort
        elif self._should_send_reasoning_format():
            payload["reasoning_format"] = self._config.reasoning_format

        if can_use_tools and provider_tools:
            payload["tools"] = provider_tools
            payload["tool_choice"] = tool_choice
            if parallel_tool_calls and self._capabilities.supports_parallel_tool_calls is not False:
                payload["parallel_tool_calls"] = True

        if response_format and self._capabilities.supports_response_format is not False:
            payload["response_format"] = response_format
        if stop:
            payload["stop"] = stop
        if grammar:
            payload["grammar"] = grammar

        if stream or on_token is not None:
            if self._capabilities.supports_stream is not False:
                payload["stream"] = True
            return self._stream_chat_completion(
                payload=payload,
                on_token=on_token,
                on_reasoning=on_reasoning,
            )

        try:
            resp, used_fallback = self._post_with_compat_fallback(self._chat_endpoint, payload)
        except Exception as exc:
            return ChatCompletionResult(error=str(exc))

        if "parallel_tool_calls" in payload:
            self._capabilities.supports_parallel_tool_calls = True
        if "response_format" in payload:
            self._capabilities.supports_response_format = True
        if "reasoning_effort" in payload:
            self._capabilities.supports_reasoning_effort = True
        if "reasoning_format" in payload:
            self._capabilities.supports_reasoning_format = True

        result = self._parse_chat_completion_response(resp)
        result.used_tools_fallback = used_fallback
        return result

    def _parse_tool_calls(self, message: Dict[str, Any]) -> List[ToolCall]:
        raw_tool_calls = message.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            return []

        parsed: List[ToolCall] = []
        for i, tc in enumerate(raw_tool_calls):
            if not isinstance(tc, dict):
                continue
            raw_id = str(tc.get("id") or f"call_{i+1}")
            tc_id = sanitize_tool_call_id(raw_id, mode="strict")
            fn = tc.get("function", {})
            if not isinstance(fn, dict):
                fn = {}
            name = str(fn.get("name", "")).strip()
            if not name:
                continue
            raw_args = fn.get("arguments", "{}")
            args: Dict[str, Any]
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str):
                try:
                    parsed_args = json.loads(raw_args)
                    args = parsed_args if isinstance(parsed_args, dict) else {"raw": raw_args}
                except json.JSONDecodeError:
                    args = {"raw": raw_args}
            else:
                args = {}
            parsed.append(ToolCall(id=tc_id, name=name, arguments=args))
        return parsed

    def _extract_content(self, message: Dict[str, Any]) -> str:
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            return "".join(text_parts)
        return str(content) if content is not None else ""

    def _parse_chat_completion_response(self, resp: Dict[str, Any]) -> ChatCompletionResult:
        choices = resp.get("choices", [])
        if not choices:
            return ChatCompletionResult(raw_response=resp)

        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message", {})
        if not isinstance(message, dict):
            message = {}
        content = self._extract_content(message)
        tool_calls = self._parse_tool_calls(message)
        finish_reason = str(choice.get("finish_reason", "stop"))
        return ChatCompletionResult(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            raw_response=resp,
        )

    def _stream_chat_completion(
        self, payload: Dict[str, Any], on_token=None, on_reasoning=None
    ) -> ChatCompletionResult:
        used_fallback = False
        for _ in range(max(1, self._config.compat_retry_limit)):
            try:
                if "stream" not in payload:
                    resp, retry_used_fallback = self._post_with_compat_fallback(
                        self._chat_endpoint, payload
                    )
                    used_fallback = used_fallback or retry_used_fallback
                    result = self._parse_chat_completion_response(resp)
                    if result.content and on_token:
                        on_token(result.content)
                    result.used_tools_fallback = used_fallback
                    return result

                result = self._stream_post(
                    endpoint=self._chat_endpoint,
                    payload=payload,
                    on_token=on_token,
                    on_reasoning=on_reasoning,
                )
                self._capabilities.supports_stream = True
                if "parallel_tool_calls" in payload:
                    self._capabilities.supports_parallel_tool_calls = True
                if "response_format" in payload:
                    self._capabilities.supports_response_format = True
                if "reasoning_effort" in payload:
                    self._capabilities.supports_reasoning_effort = True
                if "reasoning_format" in payload:
                    self._capabilities.supports_reasoning_format = True
                result.used_tools_fallback = used_fallback
                return result
            except Exception as exc:
                changed, used_tools = self._apply_compat_payload_fallback(payload, str(exc))
                used_fallback = used_fallback or used_tools
                if changed:
                    continue
                return ChatCompletionResult(error=str(exc))
        return ChatCompletionResult(error="Provider compatibility retry limit reached.")

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._refresh_runtime_helpers()
        return self._transport.post(endpoint, payload)

    def _stream_post(
        self, endpoint: str, payload: Dict[str, Any], on_token=None, on_reasoning=None
    ) -> ChatCompletionResult:
        self._refresh_runtime_helpers()
        full_text = ""
        finish_reason = "stop"
        tc_parts: Dict[int, Dict[str, Any]] = {}

        for chunk in self._transport.stream_events(
            endpoint,
            payload,
            sse_data_prefix=self._config.sse_data_prefix,
            sse_done_marker=self._config.sse_done_marker,
        ):
            choice = (chunk.get("choices") or [{}])[0]
            if isinstance(choice, dict):
                finish_reason = str(choice.get("finish_reason") or finish_reason)
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            if not isinstance(delta, dict):
                delta = {}

            reasoning = delta.get("reasoning_content", "")
            if reasoning and on_reasoning:
                on_reasoning(reasoning)

            content = delta.get("content", "")
            if content:
                full_text += content
                if on_token:
                    on_token(content)

            raw_tool_calls = delta.get("tool_calls", [])
            if isinstance(raw_tool_calls, list):
                for part in raw_tool_calls:
                    if not isinstance(part, dict):
                        continue
                    idx = part.get("index", 0)
                    if not isinstance(idx, int):
                        idx = 0
                    entry = tc_parts.setdefault(idx, {"id": "", "name": "", "arguments_parts": []})
                    if isinstance(part.get("id"), str):
                        entry["id"] = part["id"]
                    fn = part.get("function", {})
                    if isinstance(fn, dict):
                        if isinstance(fn.get("name"), str):
                            entry["name"] = fn["name"]
                        if isinstance(fn.get("arguments"), str):
                            entry["arguments_parts"].append(fn["arguments"])

        tool_calls: List[ToolCall] = []
        for idx in sorted(tc_parts.keys()):
            item = tc_parts[idx]
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            raw_id = str(item.get("id") or f"call_{idx+1}")
            tc_id = sanitize_tool_call_id(raw_id, mode="strict")
            raw_args = "".join(item.get("arguments_parts", []))
            try:
                parsed_args = json.loads(raw_args) if raw_args else {}
                if not isinstance(parsed_args, dict):
                    parsed_args = {"raw": raw_args}
            except json.JSONDecodeError:
                parsed_args = {"raw": raw_args}
            tool_calls.append(ToolCall(id=tc_id, name=name, arguments=parsed_args))

        return ChatCompletionResult(
            content=full_text,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            raw_response={},
        )

    def _consume_rate_limit_slot(self) -> None:
        """Backward-compatible wrapper used by tests."""
        self._refresh_runtime_helpers()
        self._transport.consume_rate_limit_slot()

    def __del__(self):
        self.unload()
