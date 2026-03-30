from fastapi import APIRouter

from agentos.server.models import AgentConfigModel, ConfigPatch

_STUB_CONFIG = AgentConfigModel(
    project={"name": "my-fashion-agent", "version": "0.1.0"},
    llm={"model": "gemini-2.0-flash", "base_url": "https://ai.t8star.cn/v1"},
    agent={"type": "react", "max_iterations": 20},
    scope={"allow": ["./"], "deny": [".env", "*.key"]},
)


def create_config_router() -> APIRouter:
    router = APIRouter()

    @router.get("/config")
    async def get_config():
        return _STUB_CONFIG.model_dump()

    @router.patch("/config")
    async def update_config(body: ConfigPatch):
        if body.project:
            _STUB_CONFIG.project.update(body.project)
        if body.llm:
            _STUB_CONFIG.llm.update(body.llm)
        if body.agent:
            _STUB_CONFIG.agent.update(body.agent)
        if body.scope:
            _STUB_CONFIG.scope.update(body.scope)
        return _STUB_CONFIG.model_dump()

    return router
