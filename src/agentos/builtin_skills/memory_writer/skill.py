"""Memory Writer Skill — Agent 记忆系统管理

提供两个工具用于管理双层记忆系统：
- replace_section: L1 核心记忆的分区精准替换
- append_to_file: L2 扩展记忆的追加写入

工作流程:
  L1 更新: Agent 学到核心知识 → 调用 replace_section 精准替换 memory.md 中的对应分区
  L2 写入: Agent 产出长篇知识 → 调用 append_to_file 追加到 memory_store/ 下的专题文件
"""

import re
from pathlib import Path

from agentos.core.tool import tool


def _find_section_boundaries(lines: list[str], section_title: str) -> tuple[int, int] | None:
    """找到 ## section_title 的起止行号（左闭右开）。

    跳过 fenced code block 内部的 ## 行。
    使用 ^## (?!#) 确保不匹配 ### 三级标题。
    返回 (section_header_line, next_section_line_or_eof)。
    """
    h2_pattern = re.compile(r"^## (?!#)")
    target_pattern = re.compile(rf"^## {re.escape(section_title)}\s*$")
    fence_pattern = re.compile(r"^```")

    in_fence = False
    start = -1

    for i, line in enumerate(lines):
        if fence_pattern.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if start == -1:
            if target_pattern.match(line.strip()):
                start = i
        else:
            if h2_pattern.match(line.strip()):
                return (start, i)

    if start != -1:
        return (start, len(lines))
    return None


@tool
def replace_section(file_path: str, section_title: str, new_content: str) -> str:
    """替换 Markdown 文件中指定二级标题（##）分区的内容。

    用于 L1 核心记忆的精准更新。保留标题行，仅替换标题下方的内容体，
    直到下一个同级 ## 标题或文件末尾。

    Args:
        file_path: 目标 Markdown 文件的路径
        section_title: 要替换的二级标题文本（不含 ## 前缀）
        new_content: 替换后的新内容

    Returns:
        操作结果描述
    """
    path = Path(file_path)
    if not path.exists():
        return f"错误：文件 '{file_path}' 不存在"

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    boundaries = _find_section_boundaries([line.rstrip("\n\r") for line in lines], section_title)
    if boundaries is None:
        return f"错误：未找到分区 '## {section_title}'"

    start, end = boundaries
    header_line = lines[start]
    new_section = header_line + "\n" + new_content
    if not new_content.endswith("\n"):
        new_section += "\n"

    result_lines = lines[:start] + [new_section] + lines[end:]
    path.write_text("".join(result_lines), encoding="utf-8")
    return f"成功：已更新分区 '## {section_title}'"


@tool
def append_to_file(file_path: str, content: str) -> str:
    """向指定文件末尾追加内容。若文件或父目录不存在则自动创建。

    用于 L2 扩展记忆的写入和 memory_store/ 下专题文件的管理。

    Args:
        file_path: 目标文件的路径
        content: 要追加的内容

    Returns:
        操作结果描述
    """
    if not content or not content.strip():
        return "错误：内容不能为空"

    path = Path(file_path)
    created = not path.exists()

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write(content)

    if created:
        return f"成功：已创建文件 '{file_path}' 并写入内容"
    return f"成功：已追加内容到 '{file_path}'"
