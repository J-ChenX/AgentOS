import json
from collections.abc import AsyncIterator

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request


def sse_response(request: Request, event_stream: AsyncIterator[dict]) -> EventSourceResponse:
    async def generate():
        async for event in event_stream:
            seq = event.get("seq", 0)
            yield {"id": str(seq), "data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(generate(), ping=15)
