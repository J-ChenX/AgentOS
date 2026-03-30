from pathlib import Path

import pytest

from agentos.builtin_skills.file_reader.skill import read_file


class TestReadFile:
    def test_returns_content_with_line_numbers(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        result = read_file(str(f))
        assert "   1 | line1" in result
        assert "   2 | line2" in result
        assert "   3 | line3" in result

    def test_offset_returns_absolute_line_numbers(self, tmp_path):
        f = tmp_path / "test.txt"
        lines = [f"line{i}" for i in range(1, 11)]
        f.write_text("\n".join(lines), encoding="utf-8")
        result = read_file(str(f), offset=5, limit=3)
        assert "   5 | line5" in result
        assert "   6 | line6" in result
        assert "   7 | line7" in result
        assert "line1" not in result
        assert "line8" not in result

    def test_offset_zero_starts_from_beginning(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        result = read_file(str(f), offset=0, limit=2)
        assert "   1 | a" in result
        assert "   2 | b" in result
        assert "c" not in result

    def test_limit_truncates_output(self, tmp_path):
        f = tmp_path / "test.txt"
        lines = [f"line{i}" for i in range(1, 101)]
        f.write_text("\n".join(lines), encoding="utf-8")
        result = read_file(str(f), limit=5)
        assert result.count(" | ") == 5

    def test_file_not_found(self):
        result = read_file("/nonexistent/file.txt")
        assert "不存在" in result or "拒绝" in result

    def test_file_too_large(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * (1_048_577), encoding="utf-8")
        result = read_file(str(f))
        assert "1MB" in result

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = read_file(str(f))
        assert result == "" or "空" in result.lower()
