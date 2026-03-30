import pytest
from httpx import ASGITransport, AsyncClient

from agentos.core.project_config import LLMConfig
from agentos.core.runner import AgentRunner


@pytest.mark.anyio
async def test_agent_state_idle():
    from agentos.server.app import create_app

    app = create_app()
    runner = AgentRunner(llm_config=LLMConfig(model="test"))
    app.state.engine = runner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agent/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "idle"
        assert data["question"] is None


@pytest.mark.anyio
async def test_agent_state_waiting_user():
    from agentos.server.app import create_app

    app = create_app()
    runner = AgentRunner(llm_config=LLMConfig(model="test"))
    runner.state = "waiting_user"
    runner.pending_question = {"question": "continue?", "options": ["yes", "no"]}
    app.state.engine = runner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/agent/state")
        data = resp.json()
        assert data["state"] == "waiting_user"
        assert data["question"]["question"] == "continue?"
