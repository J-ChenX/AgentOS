# tests/core/test_history_store.py
from pathlib import Path

import pytest

from agentos.core.history_store import HistoryStore
from agentos.server.models import SessionRecord, TurnRecord


def make_session(session_id: str, title: str = "test", status: str = "done") -> SessionRecord:
    turn = TurnRecord(
        turn_id="t1",
        user_message="hello",
        created_at="2026-01-01T00:00:00Z",
        status=status,
    )
    return SessionRecord(
        session_id=session_id,
        title=title,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        turns=[turn],
    )


@pytest.mark.anyio
async def test_save_and_load(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    session = make_session("s1")
    await store.save_session(session)

    loaded = await store.load_session("s1")
    assert loaded is not None
    assert loaded.session_id == "s1"
    assert len(loaded.turns) == 1


@pytest.mark.anyio
async def test_load_nonexistent_returns_none(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    result = await store.load_session("does_not_exist")
    assert result is None


@pytest.mark.anyio
async def test_list_sessions_sorted_by_updated_at(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    s1 = make_session("s1")
    s1.updated_at = "2026-01-01T10:00:00Z"
    s1.title = "older"
    s2 = make_session("s2")
    s2.updated_at = "2026-01-02T10:00:00Z"
    s2.title = "newer"
    await store.save_session(s1)
    await store.save_session(s2)

    items, total = store.list_sessions()
    assert total == 2
    assert items[0]["session_id"] == "s2"  # newer first
    assert items[1]["session_id"] == "s1"


@pytest.mark.anyio
async def test_startup_sanitization_fixes_running_turns(tmp_path: Path):
    history_dir = tmp_path / "history"
    store = HistoryStore(history_dir)

    # Write a session with a running turn directly (simulates crash mid-turn)
    running_session = make_session("s_crash", status="running")
    await store.save_session(running_session)

    # Re-create store to simulate restart
    store2 = HistoryStore(history_dir)
    await store2.startup_sanitization()

    loaded = await store2.load_session("s_crash")
    assert loaded is not None
    assert loaded.turns[0].status == "error"
    assert loaded.turns[0].assistant_message is not None


@pytest.mark.anyio
async def test_startup_sanitization_leaves_done_turns(tmp_path: Path):
    history_dir = tmp_path / "history"
    store = HistoryStore(history_dir)
    await store.save_session(make_session("s_done", status="done"))

    store2 = HistoryStore(history_dir)
    await store2.startup_sanitization()

    loaded = await store2.load_session("s_done")
    assert loaded.turns[0].status == "done"


@pytest.mark.anyio
async def test_list_sessions_pagination(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    for i in range(5):
        s = make_session(f"s{i}")
        s.updated_at = f"2026-01-0{i + 1}T00:00:00Z"
        await store.save_session(s)

    items, total = store.list_sessions(limit=2, offset=0)
    assert total == 5
    assert len(items) == 2


# ── delete_session ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_session_removes_file_and_index(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    await store.save_session(make_session("s1"))
    await store.delete_session("s1")
    assert await store.load_session("s1") is None
    items, total = store.list_sessions()
    assert total == 0


@pytest.mark.anyio
async def test_delete_session_idempotent(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    # Must not raise when session doesn't exist
    await store.delete_session("nonexistent")


# ── delete_turn ───────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_turn_removes_one_turn(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    s = make_session("s1")
    t2 = TurnRecord(
        turn_id="t2",
        user_message="second",
        created_at="2026-01-01T01:00:00Z",
        status="done",
    )
    s.turns.append(t2)
    await store.save_session(s)

    await store.delete_turn("s1", "t2")

    loaded = await store.load_session("s1")
    assert loaded is not None
    assert len(loaded.turns) == 1
    assert loaded.turns[0].turn_id == "t1"


@pytest.mark.anyio
async def test_delete_turn_last_turn_deletes_session(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    await store.save_session(make_session("s1"))  # single turn t1

    await store.delete_turn("s1", "t1")

    assert await store.load_session("s1") is None
    _, total = store.list_sessions()
    assert total == 0


@pytest.mark.anyio
async def test_delete_running_turn_raises(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    await store.save_session(make_session("s1", status="running"))

    with pytest.raises(ValueError, match="running"):
        await store.delete_turn("s1", "t1")


@pytest.mark.anyio
async def test_delete_turn_missing_session_raises(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    with pytest.raises(ValueError, match="Session not found"):
        await store.delete_turn("no_such_session", "t1")


@pytest.mark.anyio
async def test_delete_turn_missing_turn_raises(tmp_path: Path):
    store = HistoryStore(tmp_path / "history")
    await store.save_session(make_session("s1"))
    with pytest.raises(ValueError, match="Turn not found"):
        await store.delete_turn("s1", "no_such_turn")
