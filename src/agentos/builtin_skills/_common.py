"""所有内置 Skill 共享的运行时上下文接口。

由 AgentRunner 在任务启动时通过 contextvars 注入真实的 FileScope 实例。
"""

import contextvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentos.core.file_scope import FileScope

# 模块级 ContextVar —— runner.py 通过显式导入此名称来 set/reset
_file_scope_var: contextvars.ContextVar["FileScope | None"] = contextvars.ContextVar(
    "file_scope", default=None
)


def get_file_scope() -> "FileScope | None":
    """获取当前任务的 FileScope 实例。由 AgentRunner 在每次 run() 启动时注入。"""
    return _file_scope_var.get()


# Skill-specific config from agent.toml [skills.<name>] — set by Runner
_skill_config_var: contextvars.ContextVar[dict[str, dict] | None] = contextvars.ContextVar(
    "skill_config", default=None
)


def get_skill_config(skill_name: str) -> dict:
    """获取指定 skill 的配置（来自 agent.toml [skills.<name>]）。"""
    all_config = _skill_config_var.get()
    if all_config is None:
        return {}
    return all_config.get(skill_name, {})
