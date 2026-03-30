from pathlib import Path

from agentos.builtin_skills._common import get_file_scope
from agentos.core.tool import tool


@tool
def write_file(file_path: str, content: str) -> str:
    """创建新文件或完整覆写已有文件。自动创建不存在的父目录。"""
    scope = get_file_scope()
    if scope is not None:
        allowed, reason = scope.check_access(file_path)
        if not allowed:
            return f"拒绝访问：{reason}"

    path = Path(file_path)
    existed = path.exists()
    old_line_count = 0

    if existed:
        try:
            old_line_count = len(path.read_text(encoding="utf-8").splitlines())
        except Exception:
            old_line_count = 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    if existed:
        return f"成功：已覆写 '{file_path}'（原文件共 {old_line_count} 行）"
    return f"成功：已创建 '{file_path}'"
