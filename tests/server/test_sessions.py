import asyncio

import pytest


@pytest.mark.anyio
async def test_create_session(sessions_client):
    resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "turn_id" in data


@pytest.mark.anyio
async def test_list_sessions_empty(sessions_client):
    resp = await sessions_client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_list_sessions_after_create(sessions_client):
    await sessions_client.post("/api/sessions", json={"user_message": "first"})
    resp = await sessions_client.get("/api/sessions")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "first"


@pytest.mark.anyio
async def test_get_session_detail(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "detail test"}
    )
    session_id = create_resp.json()["session_id"]
    resp = await sessions_client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert len(data["turns"]) == 1
    assert data["turns"][0]["user_message"] == "detail test"


@pytest.mark.anyio
async def test_get_session_404(sessions_client):
    resp = await sessions_client.get("/api/sessions/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_add_turn_idempotency(sessions_client):
    """Same turn_id + same message returns 200 without creating a duplicate."""
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "first turn"}
    )
    session_id = create_resp.json()["session_id"]

    # Wait for first turn to "finish" by streaming it
    first_turn_id = create_resp.json()["turn_id"]
    await sessions_client.get(
        f"/api/sessions/{session_id}/turns/{first_turn_id}/stream"
    )

    # Add a second turn
    turn_id = "fixed-uuid-1234"
    resp1 = await sessions_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"user_message": "second", "turn_id": turn_id},
    )
    assert resp1.status_code == 200
    assert resp1.json()["turn_id"] == turn_id

    # Retry with same turn_id — idempotent 200
    resp2 = await sessions_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"user_message": "second", "turn_id": turn_id},
    )
    assert resp2.status_code == 200

    # Session must still have exactly 2 turns
    detail = await sessions_client.get(f"/api/sessions/{session_id}")
    assert len(detail.json()["turns"]) == 2


@pytest.mark.anyio
async def test_add_turn_tamper_returns_400(sessions_client):
    """Same turn_id but different message returns 400."""
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "original"}
    )
    session_id = create_resp.json()["session_id"]
    first_turn_id = create_resp.json()["turn_id"]
    await sessions_client.get(
        f"/api/sessions/{session_id}/turns/{first_turn_id}/stream"
    )

    turn_id = "fixed-uuid-5678"
    await sessions_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"user_message": "legitimate", "turn_id": turn_id},
    )

    # Replay with different message — tamper detection
    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"user_message": "TAMPERED", "turn_id": turn_id},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_add_turn_409_when_running(sessions_client):
    """Returns 409 if a turn is already running."""
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "first"}
    )
    session_id = create_resp.json()["session_id"]

    # Without streaming the first turn, it stays 'running'
    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"user_message": "concurrent"},
    )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_stream_turn_returns_sse(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "stream me"}
    )
    data = create_resp.json()
    session_id, turn_id = data["session_id"], data["turn_id"]

    resp = await sessions_client.get(
        f"/api/sessions/{session_id}/turns/{turn_id}/stream",
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.anyio
async def test_stream_marks_turn_done(sessions_client):
    """After streaming completes, the turn status must be 'done'.
    The background task (_bg_task) is an asyncio.Task; we yield the event loop
    once after the stream finishes to let the finalization coroutine run.
    """
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "finish me"}
    )
    data = create_resp.json()
    session_id, turn_id = data["session_id"], data["turn_id"]

    await sessions_client.get(
        f"/api/sessions/{session_id}/turns/{turn_id}/stream"
    )
    # Yield to event loop so background _finalize_turn coroutine can complete
    await asyncio.sleep(0)

    detail = await sessions_client.get(f"/api/sessions/{session_id}")
    turn = next(t for t in detail.json()["turns"] if t["turn_id"] == turn_id)
    assert turn["status"] == "done"


@pytest.mark.anyio
async def test_cancel_turn(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "cancel me"}
    )
    data = create_resp.json()
    session_id, turn_id = data["session_id"], data["turn_id"]

    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/cancel"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# ── DELETE /sessions/{id} ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_delete_session_returns_204(sessions_client):
    resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "to be deleted"}
    )
    session_id = resp.json()["session_id"]

    del_resp = await sessions_client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 204

    get_resp = await sessions_client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_nonexistent_session_returns_204(sessions_client):
    # Idempotent — 204 even when session never existed
    resp = await sessions_client.delete("/api/sessions/does_not_exist")
    assert resp.status_code == 204


# ── DELETE /sessions/{id}/turns/{tid} ────────────────────────────────────────

@pytest.mark.anyio
async def test_delete_turn_returns_204(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "turn to delete"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    # Stream the turn to completion so it is no longer running
    await sessions_client.get(
        f"/api/sessions/{session_id}/turns/{turn_id}/stream"
    )

    del_resp = await sessions_client.delete(
        f"/api/sessions/{session_id}/turns/{turn_id}"
    )
    # Deleting the only turn removes the session too → session gone
    assert del_resp.status_code == 204
    assert (await sessions_client.get(f"/api/sessions/{session_id}")).status_code == 404


@pytest.mark.anyio
async def test_delete_turn_missing_session_returns_404(sessions_client):
    resp = await sessions_client.delete("/api/sessions/no_sess/turns/no_turn")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_turn_missing_turn_returns_404(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello"}
    )
    session_id = create_resp.json()["session_id"]
    resp = await sessions_client.delete(
        f"/api/sessions/{session_id}/turns/no_such_turn"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_running_turn_returns_409(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "still running"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]
    # Do NOT stream → turn stays "running"
    resp = await sessions_client.delete(
        f"/api/sessions/{session_id}/turns/{turn_id}"
    )
    assert resp.status_code == 409


# ── Annotation endpoints ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_add_annotation_returns_201(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={
            "target": "user",
            "start": 0,
            "end": 5,
            "original": "hello",
            "type": "emphasized",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["annotation_id"] != ""
    assert data["type"] == "emphasized"
    assert data["start"] == 0
    assert data["end"] == 5


@pytest.mark.anyio
async def test_annotation_persisted_in_session(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={"target": "user", "start": 0, "end": 5, "original": "hello", "type": "deleted"},
    )

    get_resp = await sessions_client.get(f"/api/sessions/{session_id}")
    turn = get_resp.json()["turns"][0]
    assert len(turn["annotations"]) == 1
    assert turn["annotations"][0]["type"] == "deleted"


@pytest.mark.anyio
async def test_annotation_original_mismatch_returns_422(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={
            "target": "user",
            "start": 0,
            "end": 5,
            "original": "WRONG",
            "type": "emphasized",
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_delete_annotation_returns_204(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    add_resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={"target": "user", "start": 0, "end": 5, "original": "hello", "type": "deleted"},
    )
    annotation_id = add_resp.json()["annotation_id"]

    del_resp = await sessions_client.delete(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations/{annotation_id}"
    )
    assert del_resp.status_code == 204

    get_resp = await sessions_client.get(f"/api/sessions/{session_id}")
    assert get_resp.json()["turns"][0]["annotations"] == []


@pytest.mark.anyio
async def test_add_replaced_annotation_without_replacement_returns_422(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={"target": "user", "start": 0, "end": 5, "original": "hello", "type": "replaced"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_add_replaced_annotation_with_replacement_returns_201(sessions_client):
    create_resp = await sessions_client.post(
        "/api/sessions", json={"user_message": "hello world"}
    )
    session_id = create_resp.json()["session_id"]
    turn_id = create_resp.json()["turn_id"]

    resp = await sessions_client.post(
        f"/api/sessions/{session_id}/turns/{turn_id}/annotations",
        json={
            "target": "user", "start": 0, "end": 5, "original": "hello",
            "type": "replaced", "replacement": "hi",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["replacement"] == "hi"
