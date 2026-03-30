from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentos.core.lock_manager import LockManager

# 权限描述（用于 CLI 展示）
PERMISSION_LABELS = {
    "file_read": "文件读取",
    "file_write": "文件写入",
    "network": "网络访问",
    "shell": "Shell 命令执行",
}


@dataclass
class PermissionCheckResult:
    allowed: bool
    unapproved: list[str] = field(default_factory=list)
    message: str = ""


def format_permissions_display(permissions: list[str]) -> list[str]:
    """将权限列表格式化为人类可读的行。"""
    lines = []
    env_vars = []
    for p in permissions:
        if p.startswith("env_vars:"):
            env_vars.append(p.split(":", 1)[1])
        elif p in PERMISSION_LABELS:
            lines.append(f"  • {p:<12} — {PERMISSION_LABELS[p]}")
        else:
            lines.append(f"  • {p}")
    if env_vars:
        lines.append(f"  • env_vars    — {', '.join(env_vars)}")
    return lines


class PermissionChecker:
    """权限审批与运行时校验。"""

    def __init__(self, lock_manager: LockManager):
        self.lock_manager = lock_manager

    def check_runtime(
        self,
        skill_name: str,
        requested_permissions: list[str],
        source: str = "git",
    ) -> PermissionCheckResult:
        """运行时权限校验。

        - builtin / local → 跳过校验（框架自带 / 用户可控）
        - git → 与 lock 文件中的 approved_permissions 比对
        """
        if source in ("builtin", "local"):
            return PermissionCheckResult(allowed=True)

        entry = self.lock_manager.get_lock(skill_name)
        if entry is None:
            return PermissionCheckResult(
                allowed=False,
                unapproved=requested_permissions,
                message=f"Skill '{skill_name}' 无锁定记录。运行 `agentos skill install`",
            )

        approved = set(entry.approved_permissions)
        unapproved = [p for p in requested_permissions if p not in approved]

        if unapproved:
            return PermissionCheckResult(
                allowed=False,
                unapproved=unapproved,
                message=f"Skill '{skill_name}' 请求了未审批的权限: {', '.join(unapproved)}",
            )

        return PermissionCheckResult(allowed=True)

    def needs_approval(self, skill_name: str, requested_permissions: list[str]) -> list[str]:
        """返回需要新增审批的权限列表。"""
        return self.lock_manager.get_new_permissions(skill_name, requested_permissions)
