"""LLM 调用层 — OpenAI 兼容接口，直接 httpx 请求（消息原样传输，不经 litellm 变换）"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agentos.core.project_config import LLMConfig


def _build_payload(
    llm_config: LLMConfig,
    messages: list[dict],
    tools: list[dict] | None,
    *,
    stream: bool,
) -> tuple[str, str, dict]:
    """Return (api_key, url, payload) for a chat completions request."""
    api_key = os.getenv(llm_config.api_key_env, "")
    base_url = llm_config.base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    url = f"{base_url}/chat/completions"

    payload: dict = {
        "model": llm_config.model,
        "messages": messages,
        "stream": stream,
        "temperature": llm_config.temperature,
    }
    if tools:
        payload["tools"] = tools
    if llm_config.max_tokens is not None:
        payload["max_tokens"] = llm_config.max_tokens

    return api_key, url, payload


async def stream_chat_completion(
    llm_config: LLMConfig,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> AsyncIterator[dict]:
    """流式 LLM 调用，直接 HTTP 请求，消息原样发送不经变换。"""
    api_key, url, payload = _build_payload(llm_config, messages, tools, stream=True)

    # Nested with is required: client.stream() depends on client  # noqa: SIM117
    async with httpx.AsyncClient(timeout=300.0) as client:  # noqa: SIM117
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                try:
                    err_json = json.loads(body)
                    api_msg = (
                        err_json.get("error", {}).get("message")
                        or err_json.get("message")
                        or body.decode("utf-8", errors="replace")
                    )
                except Exception:
                    api_msg = body.decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    message=f"HTTP {response.status_code}: {api_msg}",
                    request=response.request,
                    response=response,
                )
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue


async def chat_completion(
    llm_config: LLMConfig,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    """非流式 LLM 调用。"""
    api_key, url, payload = _build_payload(llm_config, messages, tools, stream=False)

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
