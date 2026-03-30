from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import tomlkit

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class LockEntry:
    """agent-lock.toml 中一个 Skill 的锁定记录"""

    git: str
    tag: str
    commit: str
    resolved_path: str
    approved_permissions: list[str] = field(default_factory=list)


class LockManager:
    """agent-lock.toml 读写管理器。"""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.locks: dict[str, LockEntry] = {}
        self._load()

    def _load(self):
        if not self.lock_path.exists():
            return
        doc = tomlkit.parse(self.lock_path.read_text(encoding="utf-8"))
        locks_section = doc.get("locks", {})
        for name, data in locks_section.items():
            if isinstance(data, dict):
                self.locks[name] = LockEntry(
                    git=data.get("git", ""),
                    tag=data.get("tag", ""),
                    commit=data.get("commit", ""),
                    resolved_path=data.get("resolved_path", ""),
                    approved_permissions=list(data.get("approved_permissions", [])),
                )

    def save(self):
        doc = tomlkit.document()
        meta = tomlkit.table()
        meta.add("generated_at", datetime.now(UTC).isoformat())
        meta.add("agentos_version", "0.1.0")
        doc.add("meta", meta)

        locks = tomlkit.table()
        for name, entry in sorted(self.locks.items()):
            t = tomlkit.table()
            t.add("git", entry.git)
            t.add("tag", entry.tag)
            t.add("commit", entry.commit)
            t.add("resolved_path", entry.resolved_path)
            perms = tomlkit.array()
            for p in entry.approved_permissions:
                perms.append(p)
            t.add("approved_permissions", perms)
            locks.add(name, t)
        doc.add("locks", locks)

        self.lock_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def get_lock(self, name: str) -> LockEntry | None:
        return self.locks.get(name)

    def set_lock(self, name: str, entry: LockEntry):
        self.locks[name] = entry

    def remove_lock(self, name: str):
        self.locks.pop(name, None)

    def get_new_permissions(self, name: str, requested: list[str]) -> list[str]:
        """返回 requested 中不在已审批列表中的新增权限。"""
        existing = self.locks.get(name)
        if existing is None:
            return requested
        approved = set(existing.approved_permissions)
        return [p for p in requested if p not in approved]
