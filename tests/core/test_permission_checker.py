from agentos.core.lock_manager import LockEntry, LockManager
from agentos.core.permission_checker import PermissionChecker, format_permissions_display


class TestFormatPermissionsDisplay:
    def test_formats_simple_permissions(self):
        lines = format_permissions_display(["network", "shell"])
        assert any("network" in line for line in lines)
        assert any("shell" in line for line in lines)

    def test_formats_env_vars(self):
        lines = format_permissions_display(["env_vars:API_KEY", "env_vars:SECRET"])
        assert any("API_KEY" in line for line in lines)

    def test_empty_permissions(self):
        lines = format_permissions_display([])
        assert lines == []


class TestPermissionChecker:
    def test_check_passes_when_approved(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "tool",
            LockEntry(
                git="https://example.com/tool.git",
                tag="v1.0.0",
                commit="aaa",
                resolved_path="x",
                approved_permissions=["network", "file_read"],
            ),
        )
        mgr.save()

        checker = PermissionChecker(LockManager(lock_path))
        result = checker.check_runtime("tool", ["network", "file_read"])
        assert result.allowed is True

    def test_check_fails_when_unapproved(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "tool",
            LockEntry(
                git="https://example.com/tool.git",
                tag="v1.0.0",
                commit="aaa",
                resolved_path="x",
                approved_permissions=["file_read"],
            ),
        )
        mgr.save()

        checker = PermissionChecker(LockManager(lock_path))
        result = checker.check_runtime("tool", ["file_read", "shell"])
        assert result.allowed is False
        assert "shell" in result.unapproved

    def test_check_skips_builtin(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        checker = PermissionChecker(LockManager(lock_path))
        result = checker.check_runtime("file_reader", ["file_read"], source="builtin")
        assert result.allowed is True

    def test_check_skips_local(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        checker = PermissionChecker(LockManager(lock_path))
        result = checker.check_runtime("my_tool", ["shell"], source="local")
        assert result.allowed is True
