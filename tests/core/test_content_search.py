from agentos.builtin_skills.content_search.skill import grep_files


class TestGrepFiles:
    def _make_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            "import os\ndef hello():\n    print('hello')\n", encoding="utf-8"
        )
        (tmp_path / "src" / "utils.py").write_text(
            "def helper():\n    return 42\n", encoding="utf-8"
        )
        (tmp_path / "README.md").write_text("# Hello Project\n", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("hello", encoding="utf-8")
        return tmp_path

    def test_find_pattern(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files("hello", str(tmp_path))
        assert "main.py" in result
        assert "print" in result

    def test_regex_pattern(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files(r"def \w+\(\)", str(tmp_path))
        assert "hello" in result
        assert "helper" in result

    def test_glob_filter(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files("hello", str(tmp_path), glob="*.py")
        assert "main.py" in result
        assert "README" not in result

    def test_excludes_git(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files("hello", str(tmp_path))
        assert ".git" not in result

    def test_no_matches(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files("zzz_nonexistent_zzz", str(tmp_path))
        assert "未找到" in result or result.strip() == ""

    def test_output_format(self, tmp_path):
        self._make_tree(tmp_path)
        result = grep_files("import", str(tmp_path))
        lines = [line for line in result.strip().splitlines() if ":" in line]
        assert len(lines) >= 1
        parts = lines[0].split(":")
        assert len(parts) >= 3  # file:line:content

    def test_binary_file_skipped(self, tmp_path):
        bf = tmp_path / "binary.bin"
        bf.write_bytes(b"\x00\x01\x02hello\x03")
        (tmp_path / "text.txt").write_text("hello", encoding="utf-8")
        result = grep_files("hello", str(tmp_path))
        assert "binary.bin" not in result
        assert "text.txt" in result
