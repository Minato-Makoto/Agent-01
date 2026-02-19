from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, Optional

from .agent_core import Agent, AgentConfig, StreamCallbacks
from .cli_args import (
    build_inference_config,
    find_workspace,
    get_arg,
    is_openai_api_base_url,
    load_env_file,
)
from .context import ContextBuilder
from .llm_inference import InferenceConfig, LLMInference
from .session import SessionManager
from .skills import SkillLoader
from .summarizer import Summarizer
from .tools import ToolRegistry


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _create_or_load_session(session_mgr: SessionManager, requested_id: str, ui: Any):
    if requested_id:
        session = session_mgr.load_session(requested_id)
        if session:
            return session
        ui.status(f"Session '{requested_id}' not found, creating new session.")
    return session_mgr.new_session()


def _connect_backend(llm: LLMInference, args: Any, config: InferenceConfig, ui: Any) -> bool:
    provider = str(get_arg(args, "provider", "local"))
    model = str(get_arg(args, "model", "") or "")
    server_exe = str(get_arg(args, "server_exe", "") or "")
    base_url = str(get_arg(args, "base_url", "") or "")
    api_key_env = str(get_arg(args, "api_key_env", "OPENAI_API_KEY") or "OPENAI_API_KEY")

    if provider == "local":
        if not model:
            ui.error("Missing model path for local mode.")
            return False
        if not server_exe:
            ui.error("Missing --server-exe for local mode.")
            return False

        ui.status(f"Loading model: {os.path.basename(model)}")
        ui.status(f"Server: {server_exe} ({config.host}:{config.port})")
        ui.status(
            "Reasoning controls: "
            f"format={config.reasoning_format or '(none)'} | "
            f"effort={config.reasoning_effort or '(none)'} "
            "(sent as-is; backend may ignore unsupported fields)."
        )
        if (
            str(config.reasoning_effort or "").strip()
            and str(config.reasoning_format or "").strip().lower() in {"", "auto"}
        ):
            ui.status(
                "Note: many local backends ignore reasoning_effort; use --reasoning-format none "
                "if you need to suppress visible thinking output."
            )
        if not llm.load_model(model, config, server_exe=server_exe):
            ui.error("Failed to load model.")
            return False
        return True

    if not base_url:
        ui.error("Missing --base-url for openai_compatible mode.")
        return False

    api_key = os.environ.get(api_key_env, "")
    if is_openai_api_base_url(base_url) and not api_key:
        ui.error(f"Missing API key: set environment variable {api_key_env} for OpenAI endpoint.")
        return False

    ui.status(f"Provider: {provider}")
    ui.status(f"Base URL: {base_url}")
    ui.status(f"Model ID: {config.model_id}")
    ui.status(
        "Reasoning controls: "
        f"format={config.reasoning_format or '(none)'} | "
        f"effort={config.reasoning_effort or '(none)'} "
        "(OpenAI-compatible endpoints generally prefer reasoning_effort)."
    )
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


def _build_callbacks(ui: Any) -> tuple[StreamCallbacks, Dict[str, bool]]:
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
    ui: Any,
    skill_loader: SkillLoader,
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

    if cmd == "session":
        ui.status(f"Session: {session_id}")
        ui.status(f"Messages: {session_mgr.get_message_count()}")
        return True

    return None


def _render_agent_result(ui: Any, result: str, stream_state: Dict[str, bool]) -> None:
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


def run_interactive(
    args: Any,
    *,
    ui_factory: Callable[..., Any],
    llm_factory: Callable[[], LLMInference],
) -> int:
    """Run interactive chat session with skill system."""
    ui = ui_factory(verbose=bool(get_arg(args, "verbose", False)))

    env_file = str(get_arg(args, "env_file", "") or "").strip()
    if env_file:
        env_file_abs = os.path.abspath(env_file)
        if not os.path.isfile(env_file_abs):
            ui.error(f"Env file not found: {env_file_abs}")
            return 1
        try:
            loaded = load_env_file(env_file_abs, override=False)
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
    os.environ["AGENTFORGE_WORKSPACE"] = workspace_dir

    session_mgr = SessionManager(os.path.join(workspace_dir, "sessions"))
    skill_loader = SkillLoader(workspace_dir)
    context_builder = ContextBuilder(workspace_dir)
    summarizer = Summarizer(max_tokens=config.n_ctx)
    tools = ToolRegistry()

    session_id = str(get_arg(args, "session", "") or "").strip()
    session = _create_or_load_session(session_mgr, session_id, ui)

    skills = skill_loader.discover()
    skill_count = len(skills)
    discovered_tool_count = sum(len(s.tools) for s in skills.values())

    llm = llm_factory()
    if not _connect_backend(llm, args, config, ui):
        return 1

    ui.status(f"Workspace: {workspace_dir}")
    ui.status(f"Skills discovered: {skill_count} ({discovered_tool_count} tools total)")

    max_iterations = _coerce_positive_int(get_arg(args, "max_iterations", 10), 10)
    max_repeats = _coerce_positive_int(get_arg(args, "max_repeats", 3), 3)
    agent_timeout = _coerce_positive_float(get_arg(args, "agent_timeout", 300.0), 300.0)

    agent = Agent(
        config=AgentConfig(
            workspace_dir=workspace_dir,
            max_iterations=max_iterations,
            max_repeats=max_repeats,
            timeout=agent_timeout,
            verbose=bool(get_arg(args, "verbose", False)),
        ),
        llm=llm,
        tools=tools,
        session_mgr=session_mgr,
        summarizer=summarizer,
        skill_loader=skill_loader,
        context_builder=context_builder,
    )

    provider = str(get_arg(args, "provider", "local"))

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
