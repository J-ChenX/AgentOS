from agentos.builtin_skills.file_search.skill import glob_files


class TestGlobFiles:
    def _make_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main", encoding="utf-8")
        (tmp_path / "src" / "utils.py").write_text("# utils", encoding="utf-8")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("# test", encoding="utf-8")
        (tmp_path / "README.md").write_text("# readme", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("", encoding="utf-8")
        return tmp_path

    def test_find_python_files(self, tmp_path):
        self._make_tree(tmp_path)
        result = glob_files("**/*.py", str(tmp_path))
        assert "main.py" in result
        assert "utils.py" in result
        assert "test_main.py" in result

    def test_excludes_git_directory(self, tmp_path):
        self._make_tree(tmp_path)
        result = glob_files("**/*", str(tmp_path))
        assert ".git" not in result

    def test_find_markdown(self, tmp_path):
        self._make_tree(tmp_path)
        result = glob_files("*.md", str(tmp_path))
        assert "README.md" in result

    def test_empty_results(self, tmp_path):
        self._make_tree(tmp_path)
        result = glob_files("**/*.xyz", str(tmp_path))
        assert "未找到" in result or result.strip() == ""

    def test_result_limit(self, tmp_path):
        for i in range(250):
            (tmp_path / f"file_{i}.txt").write_text("x", encoding="utf-8")
        result = glob_files("*.txt", str(tmp_path))
        lines = [
            line for line in result.strip().splitlines()
            if line.strip() and not line.startswith("⚠")
        ]
        assert len(lines) <= 200
