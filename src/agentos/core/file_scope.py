from __future__ import annotations

import fnmatch
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _strip_dot_slash(pattern: str) -> str:
    """Remove leading './' prefix from a pattern without stripping other chars."""
    if pattern.startswith("./"):
        return pattern[2:]
    return pattern


class FileScope:
    """基于 agent.toml [scope] 的文件访问控制。

    由 AgentRunner（Spec 1）在运行时创建，注入到 builtin_skills。
    每个项目/请求独立实例，不使用全局单例。
    """

    def __init__(self, project_dir: Path, allow: list[str], deny: list[str]):
        self.project_dir = project_dir.resolve()
        self.allow = allow
        self.deny = deny

    def check_access(self, target_path: str) -> tuple[bool, str]:
        """检查路径是否允许访问。

        规则（按优先级）：
        0. 拒绝绝对路径
        1. 拒绝符号链接
        2. 必须在项目目录内
        3. deny 匹配 → 拒绝
        4. allow 匹配 → 允许
        5. 默认拒绝
        """
        # 0. 拒绝绝对路径（包括 Windows 盘符如 C:\ 和 Unix 风格 /）
        if os.path.isabs(target_path) or target_path.startswith("/"):
            return False, f"拒绝访问绝对路径 '{target_path}'"

        target = self.project_dir / target_path

        # 1. 拒绝符号链接
        if target.is_symlink():
            return False, f"拒绝访问符号链接 '{target_path}'"

        resolved = target.resolve()

        # 2. 必须在项目目录内
        try:
            resolved.relative_to(self.project_dir)
        except ValueError:
            return False, f"路径 '{target_path}' 超出项目目录范围"

        rel_path = str(resolved.relative_to(self.project_dir)).replace("\\", "/")

        # 3. deny 优先
        for pattern in self.deny:
            p = _strip_dot_slash(pattern)
            if fnmatch.fnmatch(rel_path, p) or fnmatch.fnmatch(resolved.name, p):
                return False, f"路径 '{target_path}' 匹配 deny 规则 '{pattern}'"

        # 4. allow 匹配
        for pattern in self.allow:
            if pattern in ("./", "."):
                return True, "允许"
            p = _strip_dot_slash(pattern)
            if fnmatch.fnmatch(rel_path, p) or rel_path.startswith(p.rstrip("*").rstrip("/")):
                return True, "允许"

        return False, f"路径 '{target_path}' 未匹配任何 allow 规则"
