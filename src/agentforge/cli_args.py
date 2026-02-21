from __future__ import annotations

import argparse
import os
from typing import Any, Dict
from urllib.parse import urlparse

from .llm_inference import InferenceConfig


def _normalize_reasoning_effort(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = raw.replace("-", "_").replace(" ", "_")
    if normalized == "extrahigh":
        normalized = "extra_high"
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentforge",
        description="AgentForge CLI — Local agent runtime with structured tool-calling",
    )
    sub = parser.add_subparsers(dest="command")
    run_parser = sub.add_parser("run", help="Run interactive agent session")

    run_parser.add_argument(
        "model",
        nargs="?",
        default="",
        help="Path to GGUF model file (required in --provider local mode).",
    )
    run_parser.add_argument(
        "--provider",
        choices=["local", "openai_compatible"],
        default="local",
        help="Inference backend mode.",
    )
    run_parser.add_argument(
        "--server-exe",
        default="",
        help="Path to llama-server executable (required in local mode).",
    )
    run_parser.add_argument(
        "--base-url",
        default="",
        help="Base URL for remote OpenAI-compatible endpoint.",
    )
    run_parser.add_argument(
        "--model-id",
        default="",
        help="Model identifier for remote chat-completions payload.",
    )
    run_parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable that holds the API key in remote mode.",
    )

    run_parser.add_argument("-c", "--ctx-size", type=int, default=None)
    run_parser.add_argument("--gpu-layers", "-ngl", type=int, default=None)
    run_parser.add_argument("--threads", type=int, default=None)
    run_parser.add_argument("--temp", type=float, default=None)
    run_parser.add_argument("--top-p", type=float, default=None)
    run_parser.add_argument("--top-k", type=int, default=None)
    run_parser.add_argument("--repeat-penalty", type=float, default=None)
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--reasoning-effort", default="")
    run_parser.add_argument("--max-tokens", type=int, default=None)
    run_parser.add_argument("--port", type=int, default=None)
    run_parser.add_argument("--host", default="")
    run_parser.add_argument("--boot-timeout", type=int, default=None)
    run_parser.add_argument("--health-timeout", type=int, default=None)
    run_parser.add_argument("--request-timeout", type=int, default=None)
    run_parser.add_argument("--shutdown-timeout", type=int, default=None)
    run_parser.add_argument("--compat-retry-limit", type=int, default=None)
    run_parser.add_argument("--max-requests-per-minute", type=int, default=None)
    run_parser.add_argument("--max-iterations", type=int, required=True)
    run_parser.add_argument("--max-repeats", type=int, required=True)
    run_parser.add_argument("--agent-timeout", type=float, required=True)

    run_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    run_parser.add_argument("--workspace", default="", help="Path to workspace directory")
    run_parser.add_argument("--session", default="", help="Session ID to resume")
    run_parser.add_argument(
        "--env-file",
        default="",
        help="Optional .env-style file to preload environment variables.",
    )
    return parser


def get_arg(args: Any, name: str, default: Any = None) -> Any:
    return getattr(args, name, default)


def find_workspace(args: Any) -> str:
    """Resolve workspace path from CLI args or fallback project default."""
    explicit = str(get_arg(args, "workspace", "") or "").strip()
    if explicit:
        return os.path.abspath(explicit)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "workspace")


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(path: str, override: bool = False) -> Dict[str, str]:
    loaded: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = _strip_wrapping_quotes(value.strip())
            loaded[key] = value
            if override or key not in os.environ:
                os.environ[key] = value
    return loaded


def is_openai_api_base_url(base_url: str) -> bool:
    try:
        host = (urlparse(base_url or "").hostname or "").lower()
    except Exception:
        return False
    return host in {"api.openai.com"} or host.endswith(".openai.com")


def build_inference_config(args: Any) -> InferenceConfig:
    """Build effective inference config with CLI overrides only."""
    config = InferenceConfig()

    overrides = [
        ("ctx_size", "n_ctx"),
        ("gpu_layers", "n_gpu_layers"),
        ("threads", "n_threads"),
        ("temp", "temperature"),
        ("top_p", "top_p"),
        ("top_k", "top_k"),
        ("repeat_penalty", "repeat_penalty"),
        ("seed", "seed"),
        ("max_tokens", "max_tokens"),
        ("port", "port"),
        ("boot_timeout", "boot_timeout_s"),
        ("health_timeout", "health_timeout_s"),
        ("request_timeout", "request_timeout_s"),
        ("shutdown_timeout", "shutdown_timeout_s"),
        ("compat_retry_limit", "compat_retry_limit"),
        ("max_requests_per_minute", "max_requests_per_minute"),
    ]
    for arg_name, cfg_name in overrides:
        value = get_arg(args, arg_name, None)
        if value is not None:
            setattr(config, cfg_name, value)

    host = str(get_arg(args, "host", "") or "").strip()
    if host:
        config.host = host

    reasoning_effort = str(get_arg(args, "reasoning_effort", "") or "").strip()
    if reasoning_effort:
        config.reasoning_effort = _normalize_reasoning_effort(reasoning_effort)

    model_id = str(get_arg(args, "model_id", "") or "").strip()
    if model_id:
        config.model_id = model_id

    return config
