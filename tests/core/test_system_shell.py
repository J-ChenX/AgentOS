import json
import sys

import pytest

from agentos.builtin_skills.system_shell.skill import (
    _has_dangerous_operators,
    _is_safe_command,
    run_shell,
)

DEFAULT_SAFE = ["ls", "pwd", "cat", "echo", "git status", "git log", "git diff"]


class TestDangerousOperators:
    def test_redirect(self):
        assert _has_dangerous_operators("echo hello > file.txt")

    def test_append_redirect(self):
        assert _has_dangerous_operators("echo hello >> file.txt")

    def test_pipe(self):
        assert _has_dangerous_operators("cat file | grep foo")

    def test_semicolon(self):
        assert _has_dangerous_operators("ls; rm -rf /")

    def test_and_chain(self):
        assert _has_dangerous_operators("cd / && rm -rf")

    def test_or_chain(self):
        assert _has_dangerous_operators("false || rm -rf /")

    def test_subshell(self):
        assert _has_dangerous_operators("echo $(whoami)")

    def test_backtick(self):
        assert _has_dangerous_operators("echo `whoami`")

    def test_safe_command_no_operators(self):
        assert not _has_dangerous_operators("ls -la")

    def test_safe_git_status(self):
        assert not _has_dangerous_operators("git status")


class TestIsSafeCommand:
    def test_safe_single_word(self):
        assert _is_safe_command("ls", DEFAULT_SAFE)
        assert _is_safe_command("pwd", DEFAULT_SAFE)

    def test_safe_with_args(self):
        assert _is_safe_command("ls -la /tmp", DEFAULT_SAFE)
        assert _is_safe_command("echo hello", DEFAULT_SAFE)

    def test_safe_multi_word_command(self):
        assert _is_safe_command("git status", DEFAULT_SAFE)
        assert _is_safe_command("git log --oneline", DEFAULT_SAFE)

    def test_unsafe_command(self):
        assert not _is_safe_command("rm -rf /", DEFAULT_SAFE)
        assert not _is_safe_command("python script.py", DEFAULT_SAFE)

    def test_git_checkout_not_safe(self):
        assert not _is_safe_command("git checkout -- .", DEFAULT_SAFE)


class TestRunShellConfirmation:
    @pytest.mark.anyio
    async def test_safe_command_returns_confirm_action_when_has_operators(self):
        result = await run_shell.invoke(command="echo hello > file.txt")
        parsed = json.loads(result)
        assert parsed["_action"] == "confirm_and_execute"

    @pytest.mark.anyio
    async def test_unsafe_command_returns_confirm_action(self):
        result = await run_shell.invoke(command="python script.py")
        parsed = json.loads(result)
        assert parsed["_action"] == "confirm_and_execute"
        assert "python script.py" in parsed["question"]

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix echo")
    @pytest.mark.anyio
    async def test_safe_command_executes_directly(self):
        result = await run_shell.invoke(command="echo hello_test_123")
        assert "hello_test_123" in result
        assert "_action" not in result

    @pytest.mark.anyio
    async def test_confirmed_command_executes(self):
        result = await run_shell.invoke(command="echo confirmed_test", _confirmed=True)
        assert "confirmed_test" in result

    @pytest.mark.anyio
    async def test_confirm_mode_none_skips_confirmation(self):
        from agentos.builtin_skills._common import _skill_config_var

        config = {"system_shell": {"confirm_mode": "none", "safe_commands": DEFAULT_SAFE}}
        token = _skill_config_var.set(config)
        try:
            result = await run_shell.invoke(command="python --version")
            assert "_action" not in result or "confirm" not in result
        finally:
            _skill_config_var.reset(token)
