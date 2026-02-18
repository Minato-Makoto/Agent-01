from builtin_tools.sys_ops import _shell_command, _validate_command
from builtin_tools.web_ops import _validate_url


def test_blocked_command_is_rejected():
    result = _shell_command({"command": "rm -rf /"})
    assert result.success is False
    assert "SECURITY[BLOCKED_COMMAND]" in result.error


def test_allowlisted_command_executes():
    result = _shell_command({"command": "echo hello"})
    assert result.success is True
    assert result.output["exit_code"] == 0


def test_python_inline_execution_is_blocked():
    ok, code, _ = _validate_command('python -c "print(123)"')
    assert ok is False
    assert code == "BLOCKED_PYTHON_FLAG"


def test_pip_install_is_blocked():
    ok, code, _ = _validate_command("pip install requests")
    assert ok is False
    assert code == "BLOCKED_PIP_SUBCOMMAND"


def test_web_url_policy_blocks_basic_ssrf_targets():
    ok_localhost, reason_localhost = _validate_url("http://localhost:8080")
    ok_metadata, reason_metadata = _validate_url("http://169.254.169.254/latest/meta-data/")

    assert ok_localhost is False
    assert "Blocked host" in reason_localhost
    assert ok_metadata is False
    assert "Blocked host" in reason_metadata or "private/local IP" in reason_metadata
