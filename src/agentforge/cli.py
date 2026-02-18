"""
AgentForge — CLI entry point.

This module is kept as a compatibility facade:
- parser/config logic lives in `cli_args.py`
- runtime/repl wiring lives in `cli_runtime.py`
"""

from __future__ import annotations

import sys

from .cli_args import (
    build_inference_config,
    build_parser,
    find_workspace,
    get_arg as _arg,
    is_openai_api_base_url as _is_openai_api_base_url,
    load_env_file as _load_env_file,
)
from .cli_runtime import run_interactive as _run_interactive
from .llm_inference import LLMInference
from .ui import ChatUI


def run_interactive(args) -> int:
    """Backward-compatible wrapper so monkeypatches on cli.ChatUI/LLMInference still work."""
    return _run_interactive(args, ui_factory=ChatUI, llm_factory=LLMInference)


def main() -> int:
    parser = build_parser()
    parsed = parser.parse_args()

    if not parsed.command:
        parser.print_help()
        return 0
    if parsed.command == "run":
        return run_interactive(parsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())

