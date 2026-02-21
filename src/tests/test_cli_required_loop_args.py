import pytest

from agentforge.cli_args import build_parser


def test_cli_run_requires_loop_arguments():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "dummy.gguf",
                "--provider",
                "local",
                "--server-exe",
                "llama-server.exe",
            ]
        )

