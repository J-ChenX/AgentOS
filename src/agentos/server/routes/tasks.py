from typing import Any

from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from agentos.server.models import TaskCreate, TaskCreated
from agentos.server.sse import sse_response


def create_tasks_router(engine: Any) -> APIRouter:
    router = APIRouter()

    @router.post("/tasks", response_model=TaskCreated)
    async def create_task(body: TaskCreate):
        task_id = engine.create_task_id()
        engine.register_task(task_id, body.task)
        return TaskCreated(task_id=task_id)

    @router.get("/tasks/{task_id}/stream")
    async def stream_task(task_id: str, request: Request):
        last_id = request.headers.get("Last-Event-ID")
        task = engine.get_task_detail(task_id)

        if task and task.status != "running":
            start_seq = int(last_id) if last_id else 0
            remaining = [e for e in task.events if e.get("seq", 0) > start_seq]

            async def replay():
                for event in remaining:
                    yield event

            return sse_response(request, replay())

        task_text = engine._pending_tasks.pop(task_id, "task")
        return sse_response(request, engine.run(task_id, task_text))

    @router.post("/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        engine.cancel(task_id)
        return {"status": "cancelled"}

    @router.get("/tasks")
    async def list_tasks():
        return [t.model_dump() for t in engine.get_history()]

    @router.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        record = engine.get_task_detail(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        return record.model_dump()

    return router
