"""Tests for AgentRunner streaming loop and helpers."""

from __future__ import annotations

from collections import deque
from unittest.mock import patch

import pytest

from agentos.core.project_config import LLMConfig
from agentos.core.runner import AgentRunner, _accumulate_tool_calls, _safe_json_loads
from agentos.core.tool import tool


@tool
def add(a: int, b: int) -> str:
    """Add two numbers"""
    return str(a + b)


def make_mock_stream(*stream_lists):
    """Async generator factory that pops from stream_lists in order per call."""
    queue = deque(stream_lists)

    async def mock_stream(*args, **kwargs):
        for chunk in queue.popleft():
            yield chunk

    return mock_stream


# ── Chunk helpers ──────────────────────────────────────────────────────────

TEXT_CHUNKS = [
    {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
    {"choices": [{"delta": {"content": " world"}, "finish_reason": None}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
]

TOOL_CALL_CHUNKS = [
    {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {"index": 0, "id": "call_1", "function": {"name": "add", "arguments": ""}}
                    ]
                },
                "finish_reason": None,
            }
        ]
    },
    {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "",
                            "function": {"name": "", "arguments": '{"a": 1, "b": 2}'},
                        }
                    ]
                },
                "finish_reason": None,
            }
        ]
    },
    {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
]

TEXT_RESULT_CHUNKS = [
    {"choices": [{"delta": {"content": "Result is 3"}, "finish_reason": None}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
]

TOOL_CALL_AGAIN_CHUNKS = [
    {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "cx",
                            "function": {"name": "add", "arguments": '{"a":0,"b":0}'},
                        }
                    ]
                },
                "finish_reason": None,
            }
        ]
    },
    {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
]


# ── Runner tests ───────────────────────────────────────────────────────────


class TestAgentRunnerStreaming:
    def _make(self, tools=None, max_iterations=5):
        runner = AgentRunner(
            llm_config=LLMConfig(model="gpt-4"),
            tools=tools or [add],
            max_iterations=max_iterations,
        )
        runner.register_task("t1", "prompt")
        return runner

    @pytest.mark.anyio
    async def test_text_response_yields_task_started_text_delta_done(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion", new=make_mock_stream(TEXT_CHUNKS)
        ):
            events = [e async for e in runner.run("t1", "say hi")]

        types = [e["type"] for e in events]
        assert types[0] == "task_started"
        assert "text_delta" in types
        assert types[-1] == "done"

    @pytest.mark.anyio
    async def test_text_delta_content_concatenates_to_full_text(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion", new=make_mock_stream(TEXT_CHUNKS)
        ):
            events = [e async for e in runner.run("t1", "say hi")]

        text = "".join(e["content"] for e in events if e["type"] == "text_delta")
        assert text == "Hello world"

    @pytest.mark.anyio
    async def test_all_events_have_seq_field(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion", new=make_mock_stream(TEXT_CHUNKS)
        ):
            events = [e async for e in runner.run("t1", "hi")]

        assert all("seq" in e for e in events), "Missing seq on: " + str(
            [e for e in events if "seq" not in e]
        )

    @pytest.mark.anyio
    async def test_seq_is_monotonically_increasing(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion", new=make_mock_stream(TEXT_CHUNKS)
        ):
            events = [e async for e in runner.run("t1", "hi")]

        seqs = [e["seq"] for e in events]
        assert seqs == sorted(seqs)
        assert len(seqs) == len(set(seqs))

    @pytest.mark.anyio
    async def test_tool_call_yields_skill_call_before_skill_result(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion",
            new=make_mock_stream(TOOL_CALL_CHUNKS, TEXT_RESULT_CHUNKS),
        ):
            events = [e async for e in runner.run("t1", "add")]

        types = [e["type"] for e in events]
        assert "skill_call" in types
        assert "skill_result" in types
        call_idx = types.index("skill_call")
        result_idx = types.index("skill_result")
        assert call_idx < result_idx

    @pytest.mark.anyio
    async def test_tool_call_result_stored_in_task_record(self):
        runner = self._make()
        with patch(
            "agentos.core.runner.stream_chat_completion",
            new=make_mock_stream(TOOL_CALL_CHUNKS, TEXT_RESULT_CHUNKS),
        ):
            _ = [e async for e in runner.run("t1", "add")]

        task = runner.get_task_detail("t1")
        assert task is not None
        assert task.status == "done"

    @pytest.mark.anyio
    async def test_max_iterations_yields_warning_error(self):
        runner = self._make(max_iterations=1)
        # Always returns tool_calls → never resolves
        mock = make_mock_stream(*([TOOL_CALL_AGAIN_CHUNKS] * 2))
        with patch("agentos.core.runner.stream_chat_completion", new=mock):
            events = [e async for e in runner.run("t1", "loop")]

        errors = [e for e in events if e["type"] == "error"]
        assert len(errors) == 1
        assert errors[0]["level"] == "warning"
        assert "最大迭代次数" in errors[0]["message"]

    @pytest.mark.anyio
    async def test_cancel_before_run_yields_cancelled(self):
        runner = self._make()
        runner.cancel("t1")
        with patch(
            "agentos.core.runner.stream_chat_completion", new=make_mock_stream(TEXT_CHUNKS)
        ):
            events = [e async for e in runner.run("t1", "hi")]

        assert any(e["type"] == "cancelled" for e in events)

    @pytest.mark.anyio
    async def test_llm_exception_yields_fatal_error(self):
        runner = self._make()

        async def boom(*args, **kwargs):
            raise RuntimeError("network timeout")
            yield  # make it an async generator

        with patch("agentos.core.runner.stream_chat_completion", new=boom):
            events = [e async for e in runner.run("t1", "hi")]

        errors = [e for e in events if e["type"] == "error"]
        assert errors[0]["level"] == "fatal"
        assert "LLM 调用异常" in errors[0]["message"]
        assert errors[0]["task_id"] == "t1"
        assert errors[0]["recoverable"] is False

    @pytest.mark.anyio
    async def test_invalid_json_arguments_does_not_crash_main_loop(self):
        runner = self._make()
        bad_json_chunks = [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {"name": "add", "arguments": ""},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "",
                                    "function": {"name": "", "arguments": "NOT_VALID_JSON"},
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ]
            },
            {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        ]
        mock = make_mock_stream(bad_json_chunks, TEXT_RESULT_CHUNKS)
        with patch("agentos.core.runner.stream_chat_completion", new=mock):
            events = [e async for e in runner.run("t1", "test")]

        assert any(e["type"] == "done" for e in events)


# ── Helper unit tests ──────────────────────────────────────────────────────


class TestAccumulateToolCalls:
    def test_accumulates_id_name_arguments_across_chunks(self):
        buf: dict = {}
        _accumulate_tool_calls(
            buf,
            [
                {"index": 0, "id": "call_1", "function": {"name": "fn", "arguments": ""}},
            ],
        )
        _accumulate_tool_calls(
            buf,
            [
                {"index": 0, "id": "", "function": {"name": "", "arguments": '{"k":'}},
            ],
        )
        _accumulate_tool_calls(
            buf,
            [
                {"index": 0, "id": "", "function": {"name": "", "arguments": '"v"}'}},
            ],
        )
        assert buf[0]["id"] == "call_1"
        assert buf[0]["function"]["name"] == "fn"
        assert buf[0]["function"]["arguments"] == '{"k":"v"}'

    def test_none_or_missing_fields_do_not_concat(self):
        buf: dict = {}
        _accumulate_tool_calls(buf, [{"index": 0, "id": None, "function": None}])
        assert buf[0]["id"] == ""
        assert buf[0]["function"]["name"] == ""
        assert buf[0]["function"]["arguments"] == ""

    def test_two_parallel_tool_calls_tracked_by_index(self):
        buf: dict = {}
        _accumulate_tool_calls(
            buf,
            [
                {"index": 0, "id": "c0", "function": {"name": "fn0", "arguments": ""}},
                {"index": 1, "id": "c1", "function": {"name": "fn1", "arguments": ""}},
            ],
        )
        assert buf[0]["id"] == "c0"
        assert buf[1]["id"] == "c1"


class TestSafeJsonLoads:
    def test_valid_json_returns_dict(self):
        assert _safe_json_loads('{"a": 1}') == {"a": 1}

    def test_invalid_json_returns_error_dict_with_raw(self):
        result = _safe_json_loads("NOT_JSON")
        assert "_error" in result
        assert result["_raw"] == "NOT_JSON"

    def test_empty_string_returns_error_dict(self):
        result = _safe_json_loads("")
        assert "_error" in result


class TestRunnerSystemPrompt:
    def test_system_prompt_includes_agent_md_and_memory(self, tmp_path):
        """AgentRunner should build system prompt from agent.md + memory.md."""
        from agentos.core.runner import AgentRunner

        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        (agent_dir / "agent.md").write_text("你是测试助手。", encoding="utf-8")
        (agent_dir / "memory.md").write_text(
            "# 核心记忆\n\n## 用户偏好\n\n喜欢简洁\n", encoding="utf-8"
        )

        runner = AgentRunner(
            llm_config=LLMConfig(model="test"),
            agent_dir=agent_dir,
            system_prompt_path="agent.md",
            memory_path="memory.md",
        )
        prompt = runner.system_prompt
        assert "你是测试助手。" in prompt
        assert "---" in prompt
        assert "当前核心记忆" in prompt
        assert "喜欢简洁" in prompt

    def test_system_prompt_missing_files_graceful(self, tmp_path):
        """Missing agent.md or memory.md should not crash."""
        from agentos.core.runner import AgentRunner

        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()

        runner = AgentRunner(
            llm_config=LLMConfig(model="test"),
            agent_dir=agent_dir,
            system_prompt_path="agent.md",
            memory_path="memory.md",
        )
        assert runner.system_prompt is not None
