"""System Shell Skill — 执行 shell 命令（白名单 + 操作符检测 + 确认机制）"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re

from agentos.builtin_skills._common import get_skill_config
from agentos.core.tool import tool

DEFAULT_SAFE_COMMANDS = [
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "echo",
    "wc",
    "find",
    "grep",
    "which",
    "env",
    "date",
    "whoami",
    "python --version",
    "node --version",
    "git status",
    "git log",
    "git diff",
    "pip list",
]

DANGEROUS_OPERATOR_PATTERN = re.compile(r"[|;&]|>>?|`|\$\(")
_QUOTED_STRING_PATTERN = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'')
_FILE_READ_CMDS = re.compile(r"^(cat|head|tail|less|more|type)\s+", re.IGNORECASE)
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff", ".tif"}

MAX_OUTPUT_CHARS = 10000
DEFAULT_TIMEOUT = 120


def _has_dangerous_operators(command: str) -> bool:
    """Check if command contains shell meta-characters (pipes, redirects, etc.).
    Quoted string contents are ignored so operators inside -c "...;..." don't false-positive."""
    stripped = _QUOTED_STRING_PATTERN.sub("''", command)
    return bool(DANGEROUS_OPERATOR_PATTERN.search(stripped))


def _is_safe_command(command: str, safe_commands: list[str]) -> bool:
    """Check if command's first token (or multi-word prefix) is in the safe list."""
    cmd = command.strip()
    for safe in sorted(safe_commands, key=len, reverse=True):
        if " " in safe:
            if cmd == safe or cmd.startswith(safe + " "):
                return True
        else:
            first_token = cmd.split()[0] if cmd else ""
            if first_token == safe:
                return True
    return False


def _needs_confirmation(command: str, safe_commands: list[str], confirm_mode: str) -> bool:
    """Determine if command needs user confirmation."""
    if confirm_mode == "none":
        return False
    if confirm_mode == "all":
        return True
    if _has_dangerous_operators(command):
        return True
    return not _is_safe_command(command, safe_commands)


@tool
async def run_shell(command: str, _confirmed: bool = False) -> str:
    """执行 shell 命令并返回输出（stdout + stderr）。
    非只读命令需要用户确认（可在 agent.toml 中配置确认策略）。"""
    config = get_skill_config("system_shell")
    safe_commands = config.get("safe_commands", DEFAULT_SAFE_COMMANDS)
    confirm_mode = config.get("confirm_mode", "unsafe")

    # Intercept attempts to read image files via shell — redirect to read_file
    if _FILE_READ_CMDS.match(command.strip()):
        from pathlib import Path

        parts = command.strip().split()
        if len(parts) >= 2:
            filepath = parts[-1].strip("\"'")
            if Path(filepath).suffix.lower() in _IMAGE_EXTS:
                return (
                    f"错误：不能用 shell 命令查看图片文件。"
                    f"请直接调用 read_file(file_path='{filepath}') 来查看图片内容。"
                )

    if not _confirmed and _needs_confirmation(command, safe_commands, confirm_mode):
        return json.dumps(
            {
                "_action": "confirm_and_execute",
                "question": f"确认执行命令？\n```\n{command}\n```",
                "options": ["执行", "取消"],
                "_retry_args": {"command": command, "_confirmed": True},
            },
            ensure_ascii=False,
        )

    # Execute the command asynchronously (MUST use asyncio to avoid blocking the event loop)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=DEFAULT_TIMEOUT,
        )
        output = stdout_bytes.decode("utf-8", errors="replace") + stderr_bytes.decode(
            "utf-8", errors="replace"
        )
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return f"错误：命令执行超时（{DEFAULT_TIMEOUT}秒）"
    except Exception as e:
        return f"错误：命令执行失败 — {e}"

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n\n⚠ 输出已截断（显示前 {MAX_OUTPUT_CHARS} 字符）"

    if proc.returncode != 0:
        return f"[exit code {proc.returncode}]\n{output}"

    return output if output.strip() else "(命令执行成功，无输出)"
