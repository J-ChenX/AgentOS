import asyncio

from agentos.core.project_config import LLMConfig
from agentos.core.runner import AgentRunner


class TestAgentRunnerInterface:
    def _make(self):
        return AgentRunner(llm_config=LLMConfig(model="gpt-4"))

    def test_create_task_id_starts_with_task_(self):
        runner = self._make()
        assert runner.create_task_id().startswith("task_")

    def test_create_task_id_is_unique(self):
        runner = self._make()
        ids = {runner.create_task_id() for _ in range(20)}
        assert len(ids) == 20

    def test_register_task_stores_in_pending(self):
        runner = self._make()
        runner.register_task("t1", "do something")
        assert runner._pending_tasks["t1"] == "do something"

    def test_get_history_empty_initially(self):
        assert self._make().get_history() == []

    def test_get_task_detail_none_for_unknown(self):
        assert self._make().get_task_detail("nope") is None

    def test_submit_action_stores_payload(self):
        runner = self._make()
        runner.submit_action("act_1", {"choice": "yes"})
        assert runner.action_payloads["act_1"] == {"choice": "yes"}

    def test_submit_action_sets_waiter_event(self):
        runner = self._make()
        event = asyncio.Event()
        runner.action_waiters["act_2"] = event
        runner.submit_action("act_2", "payload")
        assert event.is_set()
