import os

import pytest

from agentos.core.file_scope import FileScope


class TestFileScope:
    def _make_scope(self, tmp_path, allow=None, deny=None):
        return FileScope(
            project_dir=tmp_path,
            allow=allow or ["./"],
            deny=deny or [],
        )

    def test_allows_file_in_project(self, tmp_path):
        (tmp_path / "readme.txt").write_text("hello")
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("readme.txt")
        assert allowed is True

    def test_denies_absolute_path(self, tmp_path):
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("/etc/passwd")
        assert allowed is False
        assert "绝对路径" in reason

    def test_denies_path_traversal(self, tmp_path):
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("../../etc/passwd")
        assert allowed is False
        assert "超出项目目录" in reason

    def test_deny_overrides_allow(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=123")
        scope = self._make_scope(tmp_path, deny=[".env"])
        allowed, reason = scope.check_access(".env")
        assert allowed is False
        assert "deny" in reason

    def test_deny_glob_pattern(self, tmp_path):
        (tmp_path / "secret.key").write_text("key")
        scope = self._make_scope(tmp_path, deny=["*.key"])
        allowed, reason = scope.check_access("secret.key")
        assert allowed is False

    def test_allows_subdirectory_file(self, tmp_path):
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "main.py").write_text("print(1)")
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("src/main.py")
        assert allowed is True

    def test_denies_symlink(self, tmp_path):
        target = tmp_path / "real.txt"
        target.write_text("real")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            # Windows may not support symlinks without admin
            import pytest

            pytest.skip("symlink not supported")
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("link.txt")
        assert allowed is False
        assert "符号链接" in reason

    def test_deny_directory_pattern(self, tmp_path):
        secrets = tmp_path / "secrets"
        secrets.mkdir()
        (secrets / "db.conf").write_text("password")
        scope = self._make_scope(tmp_path, deny=["secrets/*"])
        allowed, reason = scope.check_access("secrets/db.conf")
        assert allowed is False

    def test_nonexistent_file_still_checked(self, tmp_path):
        scope = self._make_scope(tmp_path, deny=["*.key"])
        allowed, reason = scope.check_access("new.key")
        assert allowed is False

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_absolute_path(self, tmp_path):
        scope = self._make_scope(tmp_path)
        allowed, reason = scope.check_access("C:\\Windows\\System32\\cmd.exe")
        assert allowed is False
