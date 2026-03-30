"""Tests for Runner _action protocol: ask_user, confirm_and_execute, todos_updated."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from unittest.mock import patch

import pytest

from agentos.core.project_config import LLMConfig
from agentos.core.runner import AgentRunner, _try_parse_action
from agentos.core.tool import tool


class TestTryParseAction:
    def test_returns_none_for_plain_text(self):
        assert _try_parse_action("hello world") is None

    def test_returns_none_for_non_action_json(self):
        assert _try_parse_action('{"key": "value"}') is None

    def test_parses_ask_user_action(self):
        data = json.dumps({"_action": "ask_user", "question": "continue?"})
        result = _try_parse_action(data)
        assert result["_action"] == "ask_user"
        assert result["question"] == "continue?"

    def test_parses_confirm_and_execute(self):
        data = json.dumps({
            "_action": "confirm_and_execute",
            "question": "run this?",
            "_retry_args": {"command": "ls", "_confirmed": True},
        })
        result = _try_parse_action(data)
        assert result["_action"] == "confirm_and_execute"
        assert result["_retry_args"]["_confirmed"] is True

    def test_parses_todos_updated(self):
        data = json.dumps({
            "_action": "todos_updated",
            "todos": [{"content": "task1", "status": "pending"}],
        })
        result = _try_parse_action(data)
        assert result["_action"] == "todos_updated"

    def test_returns_none_for_invalid_json(self):
        assert _try_parse_action("{invalid json") is None


class TestAgentRunnerState:
    def test_initial_state_is_idle(self):
        runner = AgentRunner(llm_config=LLMConfig(model="test"))
        assert runner.state == "idle"

    def test_has_pending_question(self):
        runner = AgentRunner(llm_config=LLMConfig(model="test"))
        assert runner.pending_question is None

    def test_has_todos(self):
        runner = AgentRunner(llm_config=LLMConfig(model="test"))
        assert runner.todos == []


class TestExecWithAction:
    @pytest.mark.anyio
    async def test_normal_tool_returns_result(self):
        @tool
        def greet(name: str) -> str:
            """Greet"""
            return f"hi {name}"

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[greet])
        tc = {
            "id": "c1",
            "function": {
                "name": "greet",
                "arguments": '{"name": "bob"}',
            },
        }
        name, msg = await runner.exec_tool(tc)
        assert name == "greet"
        assert msg["content"] == "hi bob"

    @pytest.mark.anyio
    async def test_ask_user_action_emits_event_and_waits(self):
        @tool
        def ask(question: str) -> str:
            """Ask"""
            return json.dumps({
                "_action": "ask_user",
                "question": question,
            })

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[ask])
        tc = {
            "id": "c1",
            "function": {
                "name": "ask",
                "arguments": '{"question": "ok?"}',
            },
        }

        async def answer_later():
            await asyncio.sleep(0.1)
            runner.submit_action("c1", {"text": "yes please"})

        asyncio.create_task(answer_later())
        name, msg = await runner.exec_tool(tc)

        assert name == "ask"
        assert msg["content"] == "yes please"
        assert runner.state == "idle"

    @pytest.mark.anyio
    async def test_confirm_and_execute_confirmed(self):
        @tool
        def dangerous(command: str, _confirmed: bool = False) -> str:
            """Run"""
            if not _confirmed:
                return json.dumps({
                    "_action": "confirm_and_execute",
                    "question": f"run {command}?",
                    "options": ["\u786e\u8ba4", "\u53d6\u6d88"],
                    "_retry_args": {
                        "command": command,
                        "_confirmed": True,
                    },
                })
            return f"executed: {command}"

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[dangerous])
        tc = {
            "id": "c2",
            "function": {
                "name": "dangerous",
                "arguments": '{"command": "rm x"}',
            },
        }

        async def confirm_later():
            await asyncio.sleep(0.1)
            runner.submit_action("c2", {"confirmed": True})

        asyncio.create_task(confirm_later())
        name, msg = await runner.exec_tool(tc)

        assert msg["content"] == "executed: rm x"

    @pytest.mark.anyio
    async def test_confirm_and_execute_cancelled(self):
        @tool
        def dangerous(command: str, _confirmed: bool = False) -> str:
            """Run"""
            if not _confirmed:
                return json.dumps({
                    "_action": "confirm_and_execute",
                    "question": f"run {command}?",
                    "options": ["\u786e\u8ba4", "\u53d6\u6d88"],
                    "_retry_args": {
                        "command": command,
                        "_confirmed": True,
                    },
                })
            return f"executed: {command}"

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[dangerous])
        tc = {
            "id": "c3",
            "function": {
                "name": "dangerous",
                "arguments": '{"command": "rm x"}',
            },
        }

        async def cancel_later():
            await asyncio.sleep(0.1)
            runner.submit_action(
                "c3", {"confirmed": False, "text": "too risky"},
            )

        asyncio.create_task(cancel_later())
        name, msg = await runner.exec_tool(tc)

        assert "\u53d6\u6d88" in msg["content"]
        assert "too risky" in msg["content"]

    @pytest.mark.anyio
    async def test_todos_updated_action(self):
        @tool
        def todos(data: str) -> str:
            """Update todos"""
            return json.dumps({
                "_action": "todos_updated",
                "todos": [
                    {"content": "task1", "status": "in_progress"},
                ],
            })

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[todos])
        tc = {
            "id": "c4",
            "function": {
                "name": "todos",
                "arguments": '{"data": "x"}',
            },
        }
        name, msg = await runner.exec_tool(tc)

        assert "\u66f4\u65b0" in msg["content"]
        assert len(runner.todos) == 1
        assert runner.todos[0]["content"] == "task1"

    @pytest.mark.anyio
    async def test_ask_user_timeout(self):
        @tool
        def ask(q: str) -> str:
            """Ask"""
            return json.dumps({"_action": "ask_user", "question": q})

        runner = AgentRunner(llm_config=LLMConfig(model="test"), tools=[ask])
        runner._user_input_timeout = 0.2  # Short timeout for test
        tc = {
            "id": "c5",
            "function": {
                "name": "ask",
                "arguments": '{"q": "hello?"}',
            },
        }

        name, msg = await runner.exec_tool(tc)
        assert "\u8d85\u8fc7" in msg["content"] or "\u8d85\u65f6" in msg["content"]


class TestRunnerSkillConfig:
    def test_runner_accepts_skills_config(self):
        skills_config = {
            "system_shell": {"safe_commands": ["ls"], "confirm_mode": "none", "source": "builtin"},
        }
        runner = AgentRunner(llm_config=LLMConfig(model="test"), skills_config=skills_config)
        assert runner._skills_config == skills_config
