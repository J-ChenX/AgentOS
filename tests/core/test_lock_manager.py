from agentos.core.lock_manager import LockEntry, LockManager


class TestLockManager:
    def test_load_empty_creates_default(self, tmp_path):
        mgr = LockManager(tmp_path / "agent-lock.toml")
        assert mgr.locks == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "web_search",
            LockEntry(
                git="https://github.com/agentos-team/web-search.git",
                tag="v1.2.0",
                commit="abc123def456",
                resolved_path="github.com/agentos-team/web-search/v1.2.0",
                approved_permissions=["network", "env_vars:TAVILY_API_KEY"],
            ),
        )
        mgr.save()

        mgr2 = LockManager(lock_path)
        assert "web_search" in mgr2.locks
        entry = mgr2.locks["web_search"]
        assert entry.git == "https://github.com/agentos-team/web-search.git"
        assert entry.tag == "v1.2.0"
        assert entry.commit == "abc123def456"
        assert "network" in entry.approved_permissions

    def test_remove_lock(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "test",
            LockEntry(
                git="https://example.com/test.git",
                tag="v1.0.0",
                commit="aaa",
                resolved_path="example.com/test/v1.0.0",
                approved_permissions=[],
            ),
        )
        mgr.save()

        mgr.remove_lock("test")
        mgr.save()

        mgr2 = LockManager(lock_path)
        assert "test" not in mgr2.locks

    def test_get_lock_returns_none_for_missing(self, tmp_path):
        mgr = LockManager(tmp_path / "agent-lock.toml")
        assert mgr.get_lock("nonexistent") is None

    def test_has_permission_change(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "tool",
            LockEntry(
                git="https://example.com/tool.git",
                tag="v1.0.0",
                commit="aaa",
                resolved_path="example.com/tool/v1.0.0",
                approved_permissions=["file_read"],
            ),
        )
        # New version requests more permissions
        new_permissions = ["file_read", "network"]
        added = mgr.get_new_permissions("tool", new_permissions)
        assert added == ["network"]

    def test_no_new_permissions_returns_empty(self, tmp_path):
        lock_path = tmp_path / "agent-lock.toml"
        mgr = LockManager(lock_path)
        mgr.set_lock(
            "tool",
            LockEntry(
                git="https://example.com/tool.git",
                tag="v1.0.0",
                commit="aaa",
                resolved_path="x",
                approved_permissions=["file_read", "network"],
            ),
        )
        added = mgr.get_new_permissions("tool", ["file_read"])
        assert added == []
