import argparse
import os
import subprocess
from pathlib import Path

from agentforge import cli, cli_runtime
from agentforge.contracts import ChatCompletionResult


class _DummyUI:
    def __init__(self, inputs, verbose=False):
        self._inputs = list(inputs)
        self.verbose = verbose

    def error(self, msg):
        return None

    def status(self, msg):
        return None

    def welcome(self, model_name, tools=None, **kwargs):
        return None

    def goodbye(self):
        return None

    def get_input(self):
        if not self._inputs:
            return "exit"
        return self._inputs.pop(0)

    def stream_start(self):
        return None

    def stream_end(self):
        return None

    def stream_token(self, token):
        return None

    def stream_reasoning(self, token):
        return None

    def show_tool_call(self, name, arguments):
        return None

    def show_tool_result(self, name, result):
        return None

    def thinking_start(self):
        return None

    def thinking_stop(self):
        return None


def test_run_bat_keeps_local_default_mode():
    run_bat = Path("run.bat").read_text(encoding="utf-8")
    assert 'set "PROVIDER=local"' in run_bat
    assert (
        'set "RUN_ARGS=run \\"%MODEL_PATH%\\" --provider local --server-exe \\"%SERVER_EXE%\\""' in run_bat
    )
    assert (
        'set "RUN_ARGS=run --provider openai_compatible --base-url \\"%BASE_URL%\\" --model-id \\"%MODEL_ID%\\" --api-key-env \\"%API_KEY_ENV%\\""' 
        in run_bat
    )


def test_run_bat_uses_crlf_line_endings():
    data = Path("run.bat").read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_run_bat_smoke_openai_compatible_help():
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PROVIDER"] = "openai_compatible"
    env["BASE_URL"] = "http://127.0.0.1:8080"
    env["MODEL_ID"] = "local"
    env["EXTRA_ARGS"] = "--help"

    proc = subprocess.run(
        ["cmd", "/c", "run.bat"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0
    assert "usage: agentforge run" in proc.stdout


def test_remote_mode_smoke_with_mock_endpoint(monkeypatch, mock_chat_server, minimal_workspace):
    mock_chat_server.enqueue_stream(
        [
            {"choices": [{"delta": {"content": "remote "}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]},
        ]
    )

    original_connect_remote = cli.LLMInference.connect_remote

    def patched_connect_remote(self, base_url, model_id, api_key="", config=None):
        ok = original_connect_remote(self, base_url, model_id, api_key, config)
        self.capabilities.supports_tools = True
        return ok

    monkeypatch.setattr(cli.LLMInference, "connect_remote", patched_connect_remote)
    monkeypatch.setattr(cli, "ChatUI", lambda verbose=False: _DummyUI(["hello", "exit"], verbose))

    args = argparse.Namespace(
        provider="openai_compatible",
        model="",
        server_exe="",
        base_url=mock_chat_server.url,
        model_id="mock",
        api_key_env="OPENAI_API_KEY",
        ctx_size=1024,
        gpu_layers=-1,
        threads=0,
        temp=0.1,
        max_tokens=128,
        port=8080,
        verbose=False,
        workspace=str(minimal_workspace),
        session="",
    )
    os.environ["OPENAI_API_KEY"] = "dummy"

    rc = cli.run_interactive(args)
    assert rc == 0
    assert len(mock_chat_server.requests) >= 1


def test_remote_openai_endpoint_requires_api_key(monkeypatch, minimal_workspace):
    monkeypatch.setattr(cli, "ChatUI", lambda verbose=False: _DummyUI(["exit"], verbose))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    args = argparse.Namespace(
        provider="openai_compatible",
        model="",
        server_exe="",
        base_url="https://api.openai.com/v1",
        model_id="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        ctx_size=1024,
        gpu_layers=-1,
        threads=0,
        temp=0.1,
        max_tokens=128,
        port=8080,
        verbose=False,
        workspace=str(minimal_workspace),
        session="",
    )

    rc = cli.run_interactive(args)
    assert rc == 1


def test_local_mode_smoke_without_starting_real_server(monkeypatch, minimal_workspace):
    monkeypatch.setattr(cli, "ChatUI", lambda verbose=False: _DummyUI(["hello", "exit"], verbose))

    def fake_load_model(self, model_path, config=None, server_exe=""):
        self._loaded = True
        self.capabilities.supports_tools = True
        return True

    def fake_chat_completion(self, messages, **kwargs):
        on_token = kwargs.get("on_token")
        if on_token:
            on_token("ok")
        return ChatCompletionResult(content="ok")

    def fake_unload(self):
        self._loaded = False

    monkeypatch.setattr(cli.LLMInference, "load_model", fake_load_model)
    monkeypatch.setattr(cli.LLMInference, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(cli.LLMInference, "unload", fake_unload)

    args = argparse.Namespace(
        provider="local",
        model="dummy.gguf",
        server_exe="llama-server.exe",
        base_url="",
        model_id="local",
        api_key_env="OPENAI_API_KEY",
        ctx_size=1024,
        gpu_layers=-1,
        threads=0,
        temp=0.1,
        max_tokens=128,
        port=8080,
        verbose=False,
        workspace=str(minimal_workspace),
        session="",
    )

    rc = cli.run_interactive(args)
    assert rc == 0


def test_runtime_applies_agent_loop_overrides(monkeypatch, minimal_workspace):
    captured = {}

    class _FakeAgent:
        def __init__(self, config, **kwargs):
            captured["config"] = config

        def run(self, user_input, callbacks=None):
            return "ok"

        def reset(self):
            return None

    monkeypatch.setattr(cli_runtime, "Agent", _FakeAgent)
    monkeypatch.setattr(cli, "ChatUI", lambda verbose=False: _DummyUI(["exit"], verbose))

    def fake_load_model(self, model_path, config=None, server_exe=""):
        self._loaded = True
        self.capabilities.supports_tools = True
        return True

    def fake_unload(self):
        self._loaded = False

    monkeypatch.setattr(cli.LLMInference, "load_model", fake_load_model)
    monkeypatch.setattr(cli.LLMInference, "unload", fake_unload)

    args = argparse.Namespace(
        provider="local",
        model="dummy.gguf",
        server_exe="llama-server.exe",
        base_url="",
        model_id="local",
        api_key_env="OPENAI_API_KEY",
        ctx_size=1024,
        gpu_layers=-1,
        threads=0,
        temp=0.1,
        max_tokens=128,
        port=8080,
        verbose=False,
        workspace=str(minimal_workspace),
        session="",
        max_iterations=17,
        max_repeats=5,
        agent_timeout=42.5,
    )

    rc = cli.run_interactive(args)
    assert rc == 0
    assert captured["config"].max_iterations == 17
    assert captured["config"].max_repeats == 5
    assert captured["config"].timeout == 42.5
