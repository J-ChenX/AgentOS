from pathlib import Path

from agentos.builtin_skills._common import get_file_scope
from agentos.core.tool import tool


@tool
def edit_file(
    file_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    expected_snippet: str = "",
) -> str:
    """替换文件指定行范围的内容。start_line 和 end_line 均为 1-based 且包含两端。

    ⚠ 重要：每次 edit_file 可能改变文件总行数。对同一文件多次编辑时，
    必须在每次 edit_file 后重新调用 read_file 获取最新行号，禁止基于旧行号连续操作。

    expected_snippet（可选）：预期被替换区域的首行内容片段。提供后系统会校验，
    防止因并发修改导致行号错位。

    返回替换后受影响区域的上下文（前后各 3 行，带绝对行号）。"""
    scope = get_file_scope()
    if scope is not None:
        allowed, reason = scope.check_access(file_path)
        if not allowed:
            return f"拒绝访问：{reason}"

    path = Path(file_path)
    if not path.exists():
        return f"错误：文件 '{file_path}' 不存在"

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"错误：'{file_path}' 不是文本文件"

    lines = text.splitlines()
    total = len(lines)

    # Boundary validation
    if start_line < 1:
        return f"错误：start_line ({start_line}) 不能小于 1"
    if end_line > total:
        return f"错误：end_line ({end_line}) 超出文件总行数 ({total})"
    if start_line > end_line:
        return f"错误：start_line ({start_line}) 不能大于 end_line ({end_line})"

    # Concurrent modification guard
    if expected_snippet and expected_snippet.strip():
        actual_first_line = lines[start_line - 1]
        if expected_snippet.strip() not in actual_first_line.strip():
            return (
                f"⚠ 行号 {start_line} 的内容与预期不符，可能文件已被外部修改。"
                f"当前第 {start_line} 行内容为：'{actual_first_line.strip()}'。"
                f"请重新调用 read_file 获取最新内容。"
            )

    # Perform replacement
    new_lines = new_content.splitlines() if new_content else []
    lines[start_line - 1 : end_line] = new_lines

    path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")

    # Build context output (3 lines before/after the edited region)
    ctx_start = max(0, start_line - 1 - 3)
    ctx_end = min(len(lines), start_line - 1 + len(new_lines) + 3)
    ctx_lines = lines[ctx_start:ctx_end]

    width = max(len(str(ctx_end)), 4)
    output = []
    for i, line in enumerate(ctx_lines, start=ctx_start + 1):
        output.append(f"{i:>{width}} | {line}")

    return f"成功：已替换第 {start_line}-{end_line} 行。\n\n" + "\n".join(output)
