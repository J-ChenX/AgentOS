import pytest


@pytest.mark.anyio
async def test_list_skills(client):
    resp = await client.get("/api/skills")
    assert resp.status_code == 200
    skills = resp.json()
    assert len(skills) > 0
    assert "name" in skills[0]


@pytest.mark.anyio
async def test_toggle_skill(client):
    resp = await client.patch("/api/skills/fetch_image", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.anyio
async def test_list_files(client):
    resp = await client.get("/api/files")
    assert resp.status_code == 200
    files = resp.json()
    assert len(files) > 0


@pytest.mark.anyio
async def test_get_config(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    config = resp.json()
    assert "project" in config
    assert "llm" in config


@pytest.mark.anyio
async def test_update_config(client):
    resp = await client.patch("/api/config", json={"project": {"name": "updated"}})
    assert resp.status_code == 200
    assert resp.json()["project"]["name"] == "updated"


@pytest.mark.anyio
async def test_submit_action(client):
    resp = await client.post("/api/actions/act_001", json={"payload": {"choice": "confirm"}})
    assert resp.status_code == 200
