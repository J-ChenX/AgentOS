from agentos.builtin_skills.file_editor.skill import edit_file


SAMPLE_CODE = """\
import os
from pathlib import Path

def hello():
    print("hello")

def world():
    print("world")

if __name__ == "__main__":
    hello()
"""


class TestEditFile:
    def test_replace_single_line(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 5, 5, '    print("HELLO")')
        content = f.read_text(encoding="utf-8")
        assert '    print("HELLO")' in content
        assert '    print("hello")' not in content
        # Result should show context with line numbers
        assert " | " in result

    def test_replace_multiple_lines(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        edit_file(str(f), 4, 5, 'def greet():\n    print("greet")')
        content = f.read_text(encoding="utf-8")
        assert "def greet():" in content
        assert "def hello():" not in content

    def test_start_line_less_than_1(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 0, 2, "new")
        assert "错误" in result

    def test_end_line_exceeds_total(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\n", encoding="utf-8")
        result = edit_file(str(f), 1, 999, "new")
        assert "错误" in result

    def test_start_greater_than_end(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 5, 3, "new")
        assert "错误" in result

    def test_expected_snippet_matches(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 4, 5, 'def greet():\n    pass', expected_snippet="def hello")
        assert "错误" not in result
        content = f.read_text(encoding="utf-8")
        assert "def greet():" in content

    def test_expected_snippet_mismatch(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 4, 5, 'new code', expected_snippet="def world")
        assert "不符" in result or "错误" in result
        # File should NOT be modified
        assert f.read_text(encoding="utf-8") == SAMPLE_CODE

    def test_context_lines_in_result(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        result = edit_file(str(f), 5, 5, '    print("HELLO")')
        # Should show surrounding context (3 lines before/after)
        assert "def hello" in result  # line 4, before edit region
        assert "def world" in result  # line 7 (now), after edit region

    def test_file_not_found(self):
        result = edit_file("/nonexistent.py", 1, 1, "x")
        assert "不存在" in result or "拒绝" in result
