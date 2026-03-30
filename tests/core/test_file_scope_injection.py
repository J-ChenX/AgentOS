"""Verify that concurrent asyncio tasks each see their own FileScope via ContextVar."""

import asyncio

import pytest

from agentos.builtin_skills._common import _file_scope_var, get_file_scope
from agentos.core.file_scope import FileScope


@pytest.mark.anyio
async def test_concurrent_tasks_do_not_share_file_scope(tmp_path):
    scope_a = FileScope(tmp_path, allow=["a/"], deny=[])
    scope_b = FileScope(tmp_path, allow=["b/"], deny=[])
    seen_a: list = []
    seen_b: list = []

    async def task_a():
        tok = _file_scope_var.set(scope_a)
        try:
            await asyncio.sleep(0)  # yield control to task_b
            seen_a.append(get_file_scope())
            await asyncio.sleep(0)
            seen_a.append(get_file_scope())
        finally:
            _file_scope_var.reset(tok)

    async def task_b():
        tok = _file_scope_var.set(scope_b)
        try:
            await asyncio.sleep(0)
            seen_b.append(get_file_scope())
            await asyncio.sleep(0)
            seen_b.append(get_file_scope())
        finally:
            _file_scope_var.reset(tok)

    await asyncio.gather(task_a(), task_b())

    assert all(s is scope_a for s in seen_a), f"task_a saw wrong scope: {seen_a}"
    assert all(s is scope_b for s in seen_b), f"task_b saw wrong scope: {seen_b}"
    assert len(seen_a) == 2 and len(seen_b) == 2


@pytest.mark.anyio
async def test_file_scope_is_none_outside_runner_context():
    """Without AgentRunner injection, get_file_scope() returns None."""
    assert get_file_scope() is None
