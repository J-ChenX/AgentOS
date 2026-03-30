# tests/server/test_models.py
from agentos.server.models import SessionCreated, SessionRecord, TurnCreated, TurnRecord


def test_turn_record_defaults():
    turn = TurnRecord(
        turn_id="t1",
        user_message="hello",
        created_at="2026-01-01T00:00:00Z",
        status="running",
    )
    assert turn.events == []
    assert turn.assistant_message is None
    assert turn.user_message_hash == ""


def test_session_record_defaults():
    session = SessionRecord(
        session_id="s1",
        title="hello",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert session.turns == []


def test_session_created():
    resp = SessionCreated(session_id="s1", turn_id="t1")
    assert resp.session_id == "s1"
    assert resp.turn_id == "t1"


def test_turn_created():
    resp = TurnCreated(turn_id="t1")
    assert resp.turn_id == "t1"
