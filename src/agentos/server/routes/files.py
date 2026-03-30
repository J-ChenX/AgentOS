from fastapi import APIRouter

from agentos.server.models import FileNodeModel

_STUB_FILES = [
    FileNodeModel(
        name="skills",
        path="skills",
        is_dir=True,
        children=[
            FileNodeModel(name="fetch_image.py", path="skills/fetch_image.py", is_dir=False),
            FileNodeModel(name="match_template.py", path="skills/match_template.py", is_dir=False),
        ],
    ),
    FileNodeModel(name="agent.toml", path="agent.toml", is_dir=False),
]


def create_files_router() -> APIRouter:
    router = APIRouter()

    @router.get("/files")
    async def list_files(path: str | None = None):
        return [f.model_dump() for f in _STUB_FILES]

    return router
