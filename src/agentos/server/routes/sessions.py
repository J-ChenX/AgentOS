from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from starlette.requests import Request  # noqa: TC002

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from agentos.server.models import (
    Annotation,
    AnnotationCreate,
    SessionCreate,
    SessionCreated,
    SessionRecord,
    TurnCreate,
    TurnCreated,
    TurnRecord,
)
from agentos.server.sse import sse_response

logger = logging.getLogger(__name__)

# ── Background execution buffer ───────────────────────────────────────────────
# Decouples LLM execution lifetime from SSE HTTP connections.
# If the client disconnects, the background task keeps running and events are
# buffered so a reconnect (with Last-Event-ID) can replay without duplication.


class _TurnRunner:
    """Buffers events from a background engine.run_turn task."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.done: bool = False
        self._cond: asyncio.Condition = asyncio.Condition()

    async def push(self, event: dict) -> None:
        async with self._cond:
            self.events.append(event)
            self._cond.notify_all()

    async def finish(self) -> None:
        async with self._cond:
            self.done = True
            self._cond.notify_all()

    async def subscribe(self, from_seq: int) -> AsyncIterator[dict]:
        """Yield events with seq > from_seq, blocking until new events arrive."""
        idx = 0
        # Fast-forward past events the client already received
        while idx < len(self.events) and self.events[idx].get("seq", 0) <= from_seq:
            idx += 1

        while True:
            to_yield: list[dict] = []
            should_stop = False
            async with self._cond:
                while idx >= len(self.events) and not self.done:
                    await self._cond.wait()
                to_yield = self.events[idx:]
                idx += len(to_yield)
                should_stop = self.done and idx >= len(self.events)
            for event in to_yield:
                yield event
            if should_stop:
                break


# Module-level registry: (session_id, turn_id) -> _TurnRunner
# Entries are created when a turn starts and removed when it finishes.
_runners: dict[tuple[str, str], _TurnRunner] = {}
# ─────────────────────────────────────────────────────────────────────────────


def apply_annotations(text: str, annotations: list[Annotation], target: str) -> str:
    """Return text with annotations applied for LLM context assembly.

    - deleted   → character range is removed
    - replaced  → character range substituted with annotation.replacement
    - emphasized → preserved as-is (marked for retention during future compression)

    annotations must be sorted by start, non-overlapping.
    """
    relevant = sorted(
        [a for a in annotations if a.target == target],
        key=lambda a: a.start,
    )
    if not relevant:
        return text
    parts: list[str] = []
    pos = 0
    for ann in relevant:
        if ann.start < pos:
            continue  # skip overlapping annotation (defensive guard)
        parts.append(text[pos : ann.start])
        if ann.type == "deleted":
            pass
        elif ann.type == "replaced":
            parts.append(ann.replacement or "")
        else:  # emphasized
            parts.append(text[ann.start : ann.end])
        pos = ann.end
    parts.append(text[pos:])
    return "".join(parts)


def create_sessions_router(engine: Any, store: Any) -> APIRouter:
    router = APIRouter()

    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def _finalize_turn(
        session: SessionRecord,
        turn: TurnRecord,
        status: str,
        assistant_message: str | None = None,
    ) -> None:
        turn.status = status
        turn.assistant_message = assistant_message
        session.updated_at = _now()
        await store.save_session(session)

    @router.post("/sessions", response_model=SessionCreated)
    async def create_session(body: SessionCreate):
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        now = _now()
        turn = TurnRecord(
            turn_id=turn_id,
            user_message=body.user_message,
            user_message_hash=_hash(body.user_message),
            created_at=now,
            status="running",
        )
        session = SessionRecord(
            session_id=session_id,
            title=body.user_message[:60],
            created_at=now,
            updated_at=now,
            turns=[turn],
        )
        await store.save_session(session)
        engine.register_turn(session_id, turn_id, body.user_message)
        return SessionCreated(session_id=session_id, turn_id=turn_id)

    @router.get("/sessions")
    async def list_sessions(limit: int = 50, offset: int = 0):
        items, total = store.list_sessions(limit=limit, offset=offset)
        return {"items": items, "total": total}

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session.model_dump()

    @router.post("/sessions/{session_id}/turns", response_model=TurnCreated)
    async def create_turn(session_id: str, body: TurnCreate):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Idempotency: if turn_id already exists, return it
        if body.turn_id:
            existing = next((t for t in session.turns if t.turn_id == body.turn_id), None)
            if existing:
                if _hash(body.user_message) != existing.user_message_hash:
                    raise HTTPException(
                        status_code=400,
                        detail="turn_id reused with different user_message",
                    )
                return TurnCreated(turn_id=existing.turn_id)

        # Concurrency lock: reject if any turn is currently running
        if any(t.status == "running" for t in session.turns):
            raise HTTPException(status_code=409, detail="Another turn is already running")

        turn_id = body.turn_id or f"turn_{uuid.uuid4().hex[:8]}"
        now = _now()
        turn = TurnRecord(
            turn_id=turn_id,
            user_message=body.user_message,
            user_message_hash=_hash(body.user_message),
            created_at=now,
            status="running",
        )
        session.turns.append(turn)
        session.updated_at = now
        await store.save_session(session)
        engine.register_turn(session_id, turn_id, body.user_message)
        return TurnCreated(turn_id=turn_id)

    @router.get("/sessions/{session_id}/turns/{turn_id}/stream")
    async def stream_turn(session_id: str, turn_id: str, request: Request):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        turn = next((t for t in session.turns if t.turn_id == turn_id), None)
        if not turn:
            raise HTTPException(status_code=404, detail="Turn not found")

        # Patch 1: read Last-Event-ID so reconnects don't re-send already-seen events
        last_event_id = int(request.headers.get("Last-Event-ID", "0"))

        # Replay already-completed turns (filter by last_event_id to prevent duplicates)
        if turn.status != "running":

            async def replay():
                for event in turn.events:
                    if event.get("seq", 0) > last_event_id:
                        yield event

            return sse_response(request, replay())

        # Build history from all done turns preceding this one
        history: list[dict] = []
        for t in session.turns[:-1]:
            if t.status == "done" and t.assistant_message:
                effective_user = apply_annotations(t.user_message, t.annotations, "user")
                effective_asst = apply_annotations(t.assistant_message, t.annotations, "assistant")
                history.append({"role": "user", "content": effective_user})
                history.append({"role": "assistant", "content": effective_asst})

        key = (session_id, turn_id)

        # Patch 2: start background task only once; SSE handler just subscribes to buffer.
        # The LLM task continues running even if the client disconnects and reconnects.
        if key not in _runners:
            runner = _TurnRunner()
            _runners[key] = runner

            async def _bg_task() -> None:
                text_parts: list[str] = []
                try:
                    async for event in engine.run_turn(
                        session_id, turn_id, turn.user_message, history
                    ):
                        await runner.push(event)
                        turn.events = runner.events[:]
                        if event.get("type") in ("text", "text_delta"):
                            text_parts.append(event.get("content", ""))
                    await _finalize_turn(
                        session,
                        turn,
                        status="done",
                        assistant_message="".join(text_parts) or None,
                    )
                except Exception as e:
                    logger.exception("background run_turn error: %s", e)
                    await _finalize_turn(session, turn, status="error")
                    await runner.push(
                        {
                            "type": "error",
                            "level": "fatal",
                            "message": str(e),
                            "task_id": turn_id,
                            "recoverable": False,
                            "seq": len(runner.events) + 1,
                        }
                    )
                finally:
                    await runner.finish()
                    _runners.pop(key, None)

            asyncio.create_task(_bg_task())

        return sse_response(request, _runners[key].subscribe(last_event_id))

    @router.post("/sessions/{session_id}/turns/{turn_id}/cancel")
    async def cancel_turn(session_id: str, turn_id: str):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        turn = next((t for t in session.turns if t.turn_id == turn_id), None)
        if not turn:
            raise HTTPException(status_code=404, detail="Turn not found")
        engine.cancel_turn(session_id, turn_id)
        return {"status": "cancelled"}

    @router.delete("/sessions/{session_id}", status_code=204)
    async def delete_session_route(session_id: str):
        await store.delete_session(session_id)

    @router.delete("/sessions/{session_id}/turns/{turn_id}", status_code=204)
    async def delete_turn_route(session_id: str, turn_id: str):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        turn = next((t for t in session.turns if t.turn_id == turn_id), None)
        if not turn:
            raise HTTPException(status_code=404, detail="Turn not found")
        if turn.status == "running":
            raise HTTPException(status_code=409, detail="Cannot delete a running turn")
        try:
            await store.delete_turn(session_id, turn_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post(
        "/sessions/{session_id}/turns/{turn_id}/annotations",
        status_code=201,
        response_model=Annotation,
    )
    async def add_annotation(session_id: str, turn_id: str, body: AnnotationCreate):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        turn = next((t for t in session.turns if t.turn_id == turn_id), None)
        if not turn:
            raise HTTPException(status_code=404, detail="Turn not found")

        # Determine source text
        source = turn.user_message if body.target == "user" else (turn.assistant_message or "")

        # Validate offsets (Unicode code points — Python str indexing is code-point based)
        if body.start < 0 or body.end > len(source) or body.start >= body.end:
            raise HTTPException(status_code=422, detail="Invalid start/end offsets")

        # Validate original matches actual text slice
        actual = source[body.start : body.end]
        if actual != body.original:
            raise HTTPException(
                status_code=422,
                detail=f"original mismatch: expected {actual!r}, got {body.original!r}",
            )

        # Check for overlap with existing annotations on same target
        for existing in turn.annotations:
            if existing.target != body.target:
                continue
            if not (body.end <= existing.start or body.start >= existing.end):
                raise HTTPException(
                    status_code=422, detail="Annotation overlaps with an existing annotation"
                )

        if body.type == "replaced" and not body.replacement:
            raise HTTPException(
                status_code=422, detail="replacement is required for type=replaced"
            )

        ann = Annotation(
            annotation_id=f"ann_{uuid.uuid4().hex[:8]}",
            **body.model_dump(),
        )
        turn.annotations.append(ann)
        await store.save_session(session)
        return ann

    @router.delete(
        "/sessions/{session_id}/turns/{turn_id}/annotations/{annotation_id}",
        status_code=204,
    )
    async def delete_annotation(session_id: str, turn_id: str, annotation_id: str):
        session = await store.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        turn = next((t for t in session.turns if t.turn_id == turn_id), None)
        if not turn:
            raise HTTPException(status_code=404, detail="Turn not found")
        original_count = len(turn.annotations)
        turn.annotations = [a for a in turn.annotations if a.annotation_id != annotation_id]
        if len(turn.annotations) == original_count:
            raise HTTPException(status_code=404, detail="Annotation not found")
        await store.save_session(session)

    return router
