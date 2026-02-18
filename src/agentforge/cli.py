"""
AgentForge — CLI entry point.

Runtime transport remains Chat Completions-compatible for broad provider
interoperability. Per current OpenAI docs, Responses API is recommended for
new OpenAI-native projects, but this CLI keeps Chat Completions semantics to
support local llama.cpp and third-party OpenAI-compatible endpoints.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .agent_core import Agent, AgentConfig, StreamCallbacks
from .context import ContextBuilder
from .llm_inference import InferenceConfig, LLMInference
from .memory import MemoryStore
from .session import SessionManager
from .skills import SkillLoader
from .summarizer import Summarizer
from .tools import ToolRegistry
from .ui import ChatUI


def build_parser():
    import argparse

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

    run_parser.add_argument(
        "-c",
        "--ctx-size",
        type=int,
        default=None,
        help="Context window size (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--gpu-layers",
        "-ngl",
        type=int,
        default=None,
        help="GPU layers (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="CPU threads (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--temp",
        type=float,
        default=None,
        help="Temperature (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help="Top-p sampling (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Top-k sampling (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=None,
        help="Repeat penalty (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--reasoning-format",
        default="",
        help="Provider-specific reasoning format field (llama.cpp-style endpoints).",
    )
    run_parser.add_argument(
        "--reasoning-effort",
        default="",
        help="OpenAI reasoning effort value when supported by endpoint/model.",
    )
    run_parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max generation tokens (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Local server port (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--host",
        default="",
        help="Local server host (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--boot-timeout",
        type=int,
        default=None,
        help="Server boot timeout seconds (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--health-timeout",
        type=int,
        default=None,
        help="Health probe timeout seconds (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--request-timeout",
        type=int,
        default=None,
        help="Request timeout seconds (default from InferenceConfig).",
    )
    run_parser.add_argument(
        "--compat-retry-limit",
        type=int,
        default=None,
        help="Compatibility retry attempts (default from InferenceConfig).",
    )

    run_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    run_parser.add_argument("--workspace", default="", help="Path to workspace directory")
    run_parser.add_argument("--session", default="", help="Session ID to resume")
    run_parser.add_argument(
        "--env-file",
        default="",
        help="Optional .env-style file to preload environment variables.",
    )
    return parser


def _arg(args: Any, name: str, default: Any = None) -> Any:
    return getattr(args, name, default)


def find_workspace(args) -> str:
    """Resolve workspace path from CLI args or fallback project default."""
    explicit = str(_arg(args, "workspace", "") or "").strip()
    if explicit:
        return os.path.abspath(explicit)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "workspace")


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_env_file(path: str, override: bool = False) -> Dict[str, str]:
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


def _is_openai_api_base_url(base_url: str) -> bool:
    try:
        host = (urlparse(base_url or "").hostname or "").lower()
    except Exception:
        return False
    return host in {"api.openai.com"} or host.endswith(".openai.com")


def main() -> int:
    parser = build_parser()
    parsed = parser.parse_args()

    if not parsed.command:
        parser.print_help()
        return 0
    if parsed.command == "run":
        return run_interactive(parsed)
    return 0


def build_inference_config(args) -> InferenceConfig:
    """Build effective inference config with CLI overrides only."""
    config = InferenceConfig()

    int_or_float_overrides = [
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
        ("compat_retry_limit", "compat_retry_limit"),
    ]
    for arg_name, cfg_name in int_or_float_overrides:
        value = _arg(args, arg_name, None)
        if value is not None:
            setattr(config, cfg_name, value)

    host = str(_arg(args, "host", "") or "").strip()
    if host:
        config.host = host

    reasoning_format = str(_arg(args, "reasoning_format", "") or "").strip()
    if reasoning_format:
        config.reasoning_format = reasoning_format

    reasoning_effort = str(_arg(args, "reasoning_effort", "") or "").strip()
    if reasoning_effort:
        config.reasoning_effort = reasoning_effort

    model_id = str(_arg(args, "model_id", "") or "").strip()
    if model_id:
        config.model_id = model_id

    return config


def _create_or_load_session(session_mgr: SessionManager, requested_id: str, ui: ChatUI):
    if requested_id:
        session = session_mgr.load_session(requested_id)
        if session:
            return session
        ui.status(f"Session '{requested_id}' not found, creating new session.")
    return session_mgr.new_session()


def _connect_backend(llm: LLMInference, args: Any, config: InferenceConfig, ui: ChatUI) -> bool:
    provider = str(_arg(args, "provider", "local"))
    model = str(_arg(args, "model", "") or "")
    server_exe = str(_arg(args, "server_exe", "") or "")
    base_url = str(_arg(args, "base_url", "") or "")
    api_key_env = str(_arg(args, "api_key_env", "OPENAI_API_KEY") or "OPENAI_API_KEY")

    if provider == "local":
        if not model:
            ui.error("Missing model path for local mode.")
            return False
        if not server_exe:
            ui.error("Missing --server-exe for local mode.")
            return False

        ui.status(f"Loading model: {os.path.basename(model)}")
        ui.status(f"Server: {server_exe} ({config.host}:{config.port})")
        if not llm.load_model(model, config, server_exe=server_exe):
            ui.error("Failed to load model.")
            return False
        return True

    if not base_url:
        ui.error("Missing --base-url for openai_compatible mode.")
        return False

    api_key = os.environ.get(api_key_env, "")
    if _is_openai_api_base_url(base_url) and not api_key:
        ui.error(
            f"Missing API key: set environment variable {api_key_env} for OpenAI endpoint."
        )
        return False

    ui.status(f"Provider: {provider}")
    ui.status(f"Base URL: {base_url}")
    ui.status(f"Model ID: {config.model_id}")
    ui.status(
        "Transport: Chat Completions-compatible endpoint "
        "(Responses API is recommended for new OpenAI-native projects)."
    )
    if not llm.connect_remote(
        base_url=base_url,
        model_id=config.model_id,
        api_key=api_key,
        config=config,
    ):
        ui.error("Failed to connect remote endpoint.")
        return False
    return True


def _build_callbacks(ui: ChatUI) -> tuple[StreamCallbacks, Dict[str, bool]]:
    stream_state: Dict[str, bool] = {"token_emitted": False}

    def on_token(token: str) -> None:
        stream_state["token_emitted"] = True
        ui.stream_token(token)

    def on_skill_activated(name: str) -> None:
        ui.status(f"Skill activated: {name}")

    callbacks = StreamCallbacks(
        on_token=on_token,
        on_reasoning=ui.stream_reasoning,
        on_tool_call=ui.show_tool_call,
        on_tool_result=ui.show_tool_result,
        on_stream_start=ui.stream_start,
        on_stream_end=ui.stream_end,
        on_thinking_start=ui.thinking_start,
        on_thinking_end=ui.thinking_stop,
        on_skill_activated=on_skill_activated,
    )
    return callbacks, stream_state


def _handle_command(
    cmd: str,
    *,
    agent: Agent,
    ui: ChatUI,
    skill_loader: SkillLoader,
    memory: MemoryStore,
    session_mgr: SessionManager,
    session_id: str,
) -> Optional[bool]:
    if cmd in {"exit", "quit"}:
        return False

    if cmd == "reset":
        agent.reset()
        ui.status("Conversation reset.")
        return True

    if cmd == "clear":
        os.system("cls" if sys.platform == "win32" else "clear")
        return True

    if cmd == "skills":
        ui.status(skill_loader.build_status_panel())
        return True

    if cmd == "memory":
        mem_ctx = memory.get_memory_context()
        ui.status(mem_ctx if mem_ctx else "No memory stored yet.")
        return True

    if cmd == "session":
        ui.status(f"Session: {session_id}")
        ui.status(f"Messages: {session_mgr.get_message_count()}")
        return True

    return None


def _render_agent_result(ui: ChatUI, result: str, stream_state: Dict[str, bool]) -> None:
    if result.startswith("[LLM Error:"):
        ui.error(result[1:-1])
        return
    if result.startswith("[Agent stopped:") or result.startswith("[Agent reached"):
        ui.status(result)
        return
    if result and not stream_state.get("token_emitted", False) and not result.startswith("["):
        ui.stream_start()
        ui.stream_token(result)
        ui.stream_end()


def run_interactive(args) -> int:
    """Run interactive chat session with skill system."""
    ui = ChatUI(verbose=bool(_arg(args, "verbose", False)))

    env_file = str(_arg(args, "env_file", "") or "").strip()
    if env_file:
        env_file_abs = os.path.abspath(env_file)
        if not os.path.isfile(env_file_abs):
            ui.error(f"Env file not found: {env_file_abs}")
            return 1
        try:
            loaded = _load_env_file(env_file_abs, override=False)
            ui.status(f"Loaded {len(loaded)} env vars from: {env_file_abs}")
        except (OSError, UnicodeDecodeError) as exc:
            ui.error(f"Failed to load env file: {exc}")
            return 1

    config = build_inference_config(args)

    workspace_dir = find_workspace(args)
    if not os.path.isdir(workspace_dir):
        ui.error(f"Workspace not found: {workspace_dir}")
        ui.status("Run setup to create workspace directory.")
        return 1

    session_mgr = SessionManager(os.path.join(workspace_dir, "sessions"))
    memory = MemoryStore(workspace_dir)
    skill_loader = SkillLoader(workspace_dir)
    context_builder = ContextBuilder(workspace_dir)
    summarizer = Summarizer(max_tokens=config.n_ctx)
    tools = ToolRegistry()

    session_id = str(_arg(args, "session", "") or "").strip()
    session = _create_or_load_session(session_mgr, session_id, ui)

    skills = skill_loader.discover()
    skill_count = len(skills)
    discovered_tool_count = sum(len(s.tools) for s in skills.values())

    llm = LLMInference()
    if not _connect_backend(llm, args, config, ui):
        return 1

    ui.status(f"Workspace: {workspace_dir}")
    ui.status(f"Skills discovered: {skill_count} ({discovered_tool_count} tools total)")

    agent = Agent(
        config=AgentConfig(
            workspace_dir=workspace_dir,
            max_iterations=10,
            verbose=bool(_arg(args, "verbose", False)),
        ),
        llm=llm,
        tools=tools,
        session_mgr=session_mgr,
        summarizer=summarizer,
        memory=memory,
        skill_loader=skill_loader,
        context_builder=context_builder,
    )

    provider = str(_arg(args, "provider", "local"))

    try:
        tool_names = [tool.name for tool in tools.get_all()]
        ui.welcome(
            llm.model_desc,
            tool_names,
            session_id=session.id,
            skill_count=skill_count,
            total_tool_count=discovered_tool_count,
            workspace=workspace_dir,
            provider=provider,
        )

        while True:
            line = ui.get_input()
            if line is None:
                break
            if not line:
                continue

            cmd = line.strip().lower()
            command_result = _handle_command(
                cmd,
                agent=agent,
                ui=ui,
                skill_loader=skill_loader,
                memory=memory,
                session_mgr=session_mgr,
                session_id=session.id,
            )
            if command_result is False:
                break
            if command_result is True:
                continue

            callbacks, stream_state = _build_callbacks(ui)
            result = agent.run(line, callbacks=callbacks)
            _render_agent_result(ui, result, stream_state)
    finally:
        ui.goodbye()
        llm.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
