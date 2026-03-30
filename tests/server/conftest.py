from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agentos.server.app import create_app
from agentos.server.app import create_app as create_app_with_dir


@pytest.fixture
def app(tmp_path: Path):
    return create_app(history_dir=tmp_path / "history")


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sessions_app(tmp_path: Path):
    return create_app_with_dir(history_dir=tmp_path / "history")


@pytest.fixture
async def sessions_client(sessions_app):
    transport = ASGITransport(app=sessions_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
