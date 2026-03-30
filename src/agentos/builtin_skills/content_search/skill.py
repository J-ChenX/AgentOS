import fnmatch
import re
from pathlib import Path

from agentos.builtin_skills._common import get_file_scope
from agentos.core.tool import tool

EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".mypy_cache"}
MAX_RESULTS = 100
BINARY_CHECK_SIZE = 8192


def _is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:BINARY_CHECK_SIZE]
        return b"\x00" in chunk
    except Exception:
        return True


@tool
def grep_files(pattern: str, path: str = "./", glob: str = "") -> str:
    """搜索文件内容。pattern 为正则表达式，glob 可过滤文件类型（如 '*.py'）。
    返回匹配行及所在文件路径和行号。"""
    scope = get_file_scope()
    base = Path(path)
    if not base.exists():
        return f"错误：路径 '{path}' 不存在"

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"错误：正则表达式无效 — {e}"

    matches = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        rel = str(p.relative_to(base)).replace("\\", "/")

        if glob and not fnmatch.fnmatch(p.name, glob):
            continue

        if scope is not None:
            allowed, _ = scope.check_access(rel)
            if not allowed:
                continue

        if _is_binary(p):
            continue

        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_num, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{rel}:{line_num}: {line.rstrip()}")
                if len(matches) >= MAX_RESULTS:
                    break
        if len(matches) >= MAX_RESULTS:
            break

    if not matches:
        return f"未找到匹配 '{pattern}' 的内容"

    result = "\n".join(matches)
    if len(matches) >= MAX_RESULTS:
        result += f"\n\n⚠ 结果已截断（显示前 {MAX_RESULTS} 条），请缩小搜索范围。"
    return result
