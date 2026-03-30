from pathlib import Path

from agentos.builtin_skills.file_writer.skill import write_file


class TestWriteFile:
    def test_create_new_file(self, tmp_path):
        f = tmp_path / "new.txt"
        result = write_file(str(f), "hello world")
        assert f.read_text(encoding="utf-8") == "hello world"
        assert "创建" in result

    def test_overwrite_existing_file(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("old content\nline2\nline3\n", encoding="utf-8")
        result = write_file(str(f), "new content")
        assert f.read_text(encoding="utf-8") == "new content"
        assert "覆写" in result
        assert "3" in result  # original line count

    def test_creates_parent_directories(self, tmp_path):
        f = tmp_path / "deep" / "nested" / "file.txt"
        result = write_file(str(f), "content")
        assert f.read_text(encoding="utf-8") == "content"
        assert "创建" in result

    def test_file_scope_blocks_access(self, tmp_path):
        from agentos.builtin_skills._common import _file_scope_var
        from agentos.core.file_scope import FileScope

        scope = FileScope(tmp_path, ["./"], [".env"])
        token = _file_scope_var.set(scope)
        try:
            result = write_file(".env", "secret")
            assert "拒绝" in result
        finally:
            _file_scope_var.reset(token)

    def test_writes_utf8(self, tmp_path):
        f = tmp_path / "unicode.txt"
        write_file(str(f), "你好世界 🌍")
        assert f.read_text(encoding="utf-8") == "你好世界 🌍"
