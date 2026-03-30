from typing import Any

from fastapi import APIRouter

from agentos.server.models import ActionSubmit


def create_actions_router(engine: Any) -> APIRouter:
    router = APIRouter()

    @router.post("/actions/{action_id}")
    async def submit_action(action_id: str, body: ActionSubmit):
        engine.submit_action(action_id, body.payload)
        return {"status": "ok"}

    return router
