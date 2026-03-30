from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agentos.server.models import TaskRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def _stub_events(task_id: str, task: str) -> list[dict]:
    seq = 0

    def s():
        nonlocal seq
        seq += 1
        return seq

    return [
        {"type": "task_started", "task_id": task_id, "seq": s()},
        {"type": "thinking", "content": "正在分析任务...", "seq": s()},
        {
            "type": "skill_call",
            "id": "call_001",
            "skill": "fetch_image",
            "args": {"url": "https://example.com/img.jpg"},
            "status": "running",
            "seq": s(),
        },
        {
            "type": "skill_result",
            "id": "call_001",
            "skill": "fetch_image",
            "status": "done",
            "result": {"local_path": "/tmp/img.jpg"},  # nosec B108 — stub/mock data only, not a real temp file
            "duration_ms": 980,
            "seq": s(),
        },
        {"type": "text", "content": f"处理任务: {task}", "seq": s()},
        {
            "type": "component",
            "id": "comp_001",
            "component_type": "data_table",
            "data": {"columns": ["Item", "Score"], "rows": []},
            "seq": s(),
        },
        {
            "type": "component_delta",
            "id": "comp_001",
            "op": "append",
            "path": "/rows",
            "value": {"Item": "A", "Score": 0.95},
            "seq": s(),
        },
        {"type": "done", "task_id": task_id, "summary": "任务处理完成", "seq": s()},
    ]


def _stub_turn_events(turn_id: str, user_message: str) -> list[dict]:
    seq = 0

    def s():
        nonlocal seq
        seq += 1
        return seq

    return [
        {"type": "task_started", "task_id": turn_id, "seq": s()},
        # Patch 3: emit a simulated truncation event so the full UI path can be tested
        {"type": "context_truncated", "turns_dropped": 2, "remaining_turns": 8, "seq": s()},
        {"type": "thinking", "content": "正在分析任务...", "seq": s()},
        {"type": "text", "content": f"处理: {user_message}", "seq": s()},
        {"type": "done", "task_id": turn_id, "summary": "任务处理完成", "seq": s()},
    ]


class StubEngine:
    def __init__(self):
        self.tasks: dict[str, TaskRecord] = {}
        self.action_waiters: dict[str, asyncio.Event] = {}
        self.action_payloads: dict[str, object] = {}
        self._cancelled: set[str] = set()
        self._pending_tasks: dict[str, str] = {}
        # Session/Turn state
        self._pending_turns: dict[tuple[str, str], str] = {}  # (sess_id, turn_id) -> msg
        self._cancelled_turns: set[tuple[str, str]] = set()

    async def run(self, task_id: str, task: str) -> AsyncIterator[dict]:
        events = _stub_events(task_id, task)
        stored_events: list[dict] = []

        self.tasks[task_id] = TaskRecord(
            task_id=task_id,
            created_at=datetime.now(UTC).isoformat(),
            task=task,
            status="running",
            events=[],
        )

        for event in events:
            if task_id in self._cancelled:
                cancel_evt = {"type": "cancelled", "task_id": task_id, "seq": event["seq"]}
                stored_events.append(cancel_evt)
                yield cancel_evt
                self.tasks[task_id].status = "cancelled"
                self.tasks[task_id].events = stored_events
                return

            await asyncio.sleep(0.1)
            stored_events.append(event)
            yield event

        self.tasks[task_id].status = "done"
        self.tasks[task_id].events = stored_events

    async def run_turn(
        self,
        session_id: str,
        turn_id: str,
        user_message: str,
        history: list[dict],
    ) -> AsyncIterator[dict]:
        """Stub implementation: emits synthetic events and completes immediately."""
        key = (session_id, turn_id)
        events = _stub_turn_events(turn_id, user_message)

        for event in events:
            if key in self._cancelled_turns:
                yield {"type": "cancelled", "task_id": turn_id, "seq": event["seq"]}
                return
            await asyncio.sleep(0.05)
            yield event

    def register_turn(self, session_id: str, turn_id: str, user_message: str) -> None:
        self._pending_turns[(session_id, turn_id)] = user_message

    def cancel_turn(self, session_id: str, turn_id: str) -> None:
        self._cancelled_turns.add((session_id, turn_id))

    def cancel(self, task_id: str):
        self._cancelled.add(task_id)

    def submit_action(self, action_id: str, payload: object):
        self.action_payloads[action_id] = payload
        waiter = self.action_waiters.get(action_id)
        if waiter:
            waiter.set()

    def get_history(self) -> list[TaskRecord]:
        return list(self.tasks.values())

    def get_task_detail(self, task_id: str) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def create_task_id(self) -> str:
        return f"task_{uuid.uuid4().hex[:8]}"

    def register_task(self, task_id: str, task: str):
        self._pending_tasks[task_id] = task
