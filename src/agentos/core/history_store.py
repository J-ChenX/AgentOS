from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from agentos.server.models import SessionRecord

logger = logging.getLogger(__name__)


class HistoryStore:
    def __init__(self, history_dir: Path) -> None:
        self._dir = history_dir
        self._locks: dict[str, asyncio.Lock] = {}
        # In-memory index: session_id -> {title, created_at, updated_at, last_turn_status}
        self._index: dict[str, dict] = {}

    def _lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def _path(self, session_id: str) -> Path:
        p = (self._dir / f"{session_id}.json").resolve()
        if not p.is_relative_to(self._dir.resolve()):
            raise ValueError(f"Invalid session_id: {session_id!r}")
        return p

    async def startup_sanitization(self) -> None:
        """Fix any turns left in 'running' state from a previous crash."""
        self._dir.mkdir(parents=True, exist_ok=True)
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                session = SessionRecord.model_validate(data)
                has_running = any(t.status == "running" for t in session.turns)
                if has_running:
                    for turn in session.turns:
                        if turn.status == "running":
                            turn.status = "error"
                            turn.assistant_message = (
                                "系统提示：任务执行期间服务器发生重启，此轮次已中断。"
                            )
                    await self.save_session(session)
                    logger.warning(
                        "startup_sanitization: fixed zombie turn in session %s",
                        session.session_id,
                    )
                self._index[session.session_id] = {
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "last_turn_status": session.turns[-1].status if session.turns else "done",
                }
            except Exception as e:
                logger.warning("Failed to load history file %s: %s", f, e)

    async def save_session(self, session: SessionRecord) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        async with self._lock(session.session_id):
            self._path(session.session_id).write_text(
                session.model_dump_json(indent=2), encoding="utf-8"
            )
            self._index[session.session_id] = {
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "last_turn_status": session.turns[-1].status if session.turns else "done",
            }

    async def load_session(self, session_id: str) -> SessionRecord | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        async with self._lock(session_id):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return SessionRecord.model_validate(data)
            except Exception as e:
                logger.error("Failed to load session %s: %s", session_id, e)
                return None

    def list_sessions(self, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        """Return (items, total). Items sorted by updated_at descending."""
        items = [
            {
                "session_id": sid,
                "title": meta["title"],
                "created_at": meta["created_at"],
                "updated_at": meta["updated_at"],
                # Minimal turns stub so frontend can read .at(-1)?.status
                "turns": [{"status": meta["last_turn_status"]}],
            }
            for sid, meta in self._index.items()
        ]
        items.sort(key=lambda x: x["updated_at"], reverse=True)
        total = len(items)
        return items[offset : offset + limit], total

    async def delete_session(self, session_id: str) -> None:
        """Delete a session file and remove it from the in-memory index. Idempotent."""
        path = self._path(session_id)
        async with self._lock(session_id):
            if path.exists():
                path.unlink()
            self._index.pop(session_id, None)

    async def delete_turn(self, session_id: str, turn_id: str) -> None:
        """Remove one turn from a session.

        Raises ValueError if the session/turn does not exist or the turn is running.
        If removing the last turn, deletes the entire session.
        """
        path = self._path(session_id)
        async with self._lock(session_id):
            if not path.exists():
                raise ValueError(f"Session not found: {session_id!r}")
            data = json.loads(path.read_text(encoding="utf-8"))
            session = SessionRecord.model_validate(data)
            turn = next((t for t in session.turns if t.turn_id == turn_id), None)
            if not turn:
                raise ValueError(f"Turn not found: {turn_id!r}")
            if turn.status == "running":
                raise ValueError(f"Cannot delete a running turn: {turn_id!r}")
            session.turns = [t for t in session.turns if t.turn_id != turn_id]
            if not session.turns:
                path.unlink()
                self._index.pop(session_id, None)
            else:
                path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
                self._index[session_id] = {
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "last_turn_status": session.turns[-1].status,
                }
