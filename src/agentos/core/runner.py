"""AgentRunner — streaming ReAct loop with FileScope injection via contextvars."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agentos.builtin_skills._common import _file_scope_var, _skill_config_var
from agentos.core.llm import stream_chat_completion
from agentos.server.models import TaskRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from agentos.core.file_scope import FileScope
    from agentos.core.project_config import LLMConfig
    from agentos.core.tool import ToolSpec


# finish_reasons that mean "the LLM is done generating" (not a tool call).
# content_filter / length are terminal states, not errors — handle gracefully.
_DONE_REASONS: frozenset[str] = frozenset(
    {"stop", "end_turn", "length", "content_filter", "content_management_policy"}
)

# Human-readable notes for non-stop terminal reasons (shown when no text was produced).
_DONE_REASON_NOTES: dict[str, str] = {
    "content_filter": "[内容被安全过滤器拦截，未能生成响应]",
    "content_management_policy": "[内容被安全策略拦截，未能生成响应]",
    "length": "[响应因超出最大长度限制而被截断]",
}

# ── Module-level helpers ───────────────────────────────────────────────────


def _accumulate_tool_calls(buf: dict[int, dict], tc_chunks: list) -> None:
    """Accumulate streaming tool_call deltas into buf keyed by index."""
    for tc_chunk in tc_chunks:
        idx = tc_chunk.get("index", 0)
        if idx not in buf:
            buf[idx] = {
                "index": idx,
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""},
            }
        entry = buf[idx]
        if tc_chunk.get("id") and not entry["id"]:
            entry["id"] = tc_chunk["id"]
        fn = tc_chunk.get("function") or {}
        if fn.get("name"):
            entry["function"]["name"] += fn["name"]
        if fn.get("arguments"):
            entry["function"]["arguments"] += fn["arguments"]


def _safe_json_loads(s: str) -> dict:
    """Parse JSON string; on failure return error dict instead of raising."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"_raw": s, "_error": "arguments JSON 解析失败"}


def _try_parse_action(result: str | list) -> dict | None:
    """Check if a tool result is a special _action JSON. Returns parsed dict or None."""
    if not isinstance(result, str) or not result.startswith("{"):
        return None
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "_action" in parsed:
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return None


class _ThinkParser:
    """Route <think>...</think> content to thinking; pass everything else through.

    Handles tags that are split across streaming chunk boundaries by buffering
    partial tag characters until a complete tag (or non-tag) is confirmed.
    """

    _OPEN = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._in_think = False
        self._tag_buf = ""  # partial tag characters being accumulated

    def feed(self, chunk: str) -> tuple[str, str]:
        """Process one streaming text chunk.

        Returns ``(text_out, think_out)`` — content for text_delta and thinking
        respectively.
        """
        text_out = ""
        think_out = ""

        for char in chunk:
            if self._tag_buf:
                self._tag_buf += char
                target = self._CLOSE if self._in_think else self._OPEN
                if target.startswith(self._tag_buf):
                    if len(self._tag_buf) == len(target):
                        # Complete tag matched — flip think mode
                        self._in_think = not self._in_think
                        self._tag_buf = ""
                    # else: still accumulating partial tag
                else:
                    # Buffer is not a prefix of any valid tag — flush as content
                    if self._in_think:
                        think_out += self._tag_buf
                    else:
                        text_out += self._tag_buf
                    self._tag_buf = ""
            elif char == "<":
                self._tag_buf = "<"
            elif self._in_think:
                think_out += char
            else:
                text_out += char

        return text_out, think_out

    def flush(self) -> tuple[str, str]:
        """Flush any partial tag buffer remaining at end of stream."""
        text_out, think_out = "", ""
        if self._tag_buf:
            if self._in_think:
                think_out = self._tag_buf
            else:
                text_out = self._tag_buf
            self._tag_buf = ""
        return text_out, think_out


async def _exec(tc: dict, tool_map: dict[str, ToolSpec]) -> tuple[str, dict]:
    """Execute one tool_call. Returns (tool_name, tool_message_dict)."""
    fn_name = tc["function"]["name"]
    try:
        fn_args = _safe_json_loads(tc["function"]["arguments"])
        ts = tool_map.get(fn_name)
        result = f"Error: unknown tool '{fn_name}'" if ts is None else await ts.invoke(**fn_args)
    except Exception as e:
        result = f"Error: {e}"
    return fn_name, {
        "role": "tool",
        "tool_call_id": tc["id"],
        "content": result,
    }


# ── AgentRunner ────────────────────────────────────────────────────────────


class AgentRunner:
    def __init__(
        self,
        llm_config: LLMConfig,
        tools: list[ToolSpec] | None = None,
        file_scope: FileScope | None = None,
        max_iterations: int = 20,
        agent_dir: Path | None = None,
        system_prompt_path: str = "agent.md",
        memory_path: str = "memory.md",
        skills_config: dict[str, dict] | None = None,
    ):
        self.llm_config = llm_config
        self.tools = tools or []
        self.file_scope = file_scope
        self.max_iterations = max_iterations
        self._tool_map: dict[str, ToolSpec] = {t.name: t for t in self.tools}
        # Engine interface fields (mirrors StubEngine for route compatibility)
        self.tasks: dict[str, TaskRecord] = {}
        self._pending_tasks: dict[str, str] = {}
        self._cancelled: set[str] = set()
        self.action_waiters: dict[str, asyncio.Event] = {}
        self.action_payloads: dict[str, object] = {}
        self._pending_turns: dict[tuple[str, str], str] = {}
        self._cancelled_turns: set[tuple[str, str]] = set()
        self._agent_dir = agent_dir
        self._system_prompt_path = system_prompt_path
        self._memory_path = memory_path
        self._skills_config = skills_config or {}
        # _action protocol state
        self.state: str = "idle"  # idle | running | waiting_user
        self.pending_question: dict | None = None
        self.todos: list[dict] = self._load_todos()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._user_input_timeout: float = 600.0  # seconds

    # ── Todo persistence ────────────────────────────────────────────────────

    def _save_todos(self, todos: list[dict]) -> None:
        """Persist todos to memory_store/todos.json."""
        if self._agent_dir is None:
            return
        store_dir = self._agent_dir / "memory_store"
        store_dir.mkdir(parents=True, exist_ok=True)
        todos_file = store_dir / "todos.json"
        todos_file.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_todos(self) -> list[dict]:
        """Load todos from memory_store/todos.json if it exists."""
        if self._agent_dir is None:
            return []
        todos_file = self._agent_dir / "memory_store" / "todos.json"
        if todos_file.exists():
            try:
                return json.loads(todos_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    # ── System prompt ──────────────────────────────────────────────────────

    @property
    def system_prompt(self) -> str:
        """Load and concatenate agent.md + memory.md with separator."""
        if self._agent_dir is None:
            return ""
        parts = []
        prompt_file = self._agent_dir / self._system_prompt_path
        if prompt_file.exists():
            parts.append(prompt_file.read_text(encoding="utf-8").strip())
        memory_file = self._agent_dir / self._memory_path
        if memory_file.exists():
            memory_content = memory_file.read_text(encoding="utf-8").strip()
            if memory_content:
                parts.append(f"\n---\n# 当前核心记忆\n\n{memory_content}")
        return "\n".join(parts)

    # ── Engine interface ───────────────────────────────────────────────────

    def create_task_id(self) -> str:
        return f"task_{uuid.uuid4().hex[:8]}"

    def register_task(self, task_id: str, task: str) -> None:
        self._pending_tasks[task_id] = task

    def get_history(self) -> list[TaskRecord]:
        return list(self.tasks.values())

    def get_task_detail(self, task_id: str) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)

    def register_turn(self, session_id: str, turn_id: str, user_message: str) -> None:
        self._pending_turns[(session_id, turn_id)] = user_message

    def cancel_turn(self, session_id: str, turn_id: str) -> None:
        self._cancelled_turns.add((session_id, turn_id))

    def submit_action(self, action_id: str, payload: object) -> None:
        self.action_payloads[action_id] = payload
        waiter = self.action_waiters.get(action_id)
        if waiter:
            waiter.set()

    # ── _action protocol ────────────────────────────────────────────────────

    async def exec_tool(self, tc: dict) -> tuple[str, dict]:
        """Execute one tool_call with _action protocol support."""
        fn_name = tc["function"]["name"]
        call_id = tc["id"]
        try:
            fn_args = _safe_json_loads(tc["function"]["arguments"])
            ts = self._tool_map.get(fn_name)
            if ts is None:
                result = f"Error: unknown tool '{fn_name}'"
            else:
                result = await ts.invoke(**fn_args)
        except Exception as e:
            result = f"Error: {e}"
            return fn_name, {"role": "tool", "tool_call_id": call_id, "content": result}

        parsed = _try_parse_action(result)
        if parsed is None:
            return fn_name, {"role": "tool", "tool_call_id": call_id, "content": result}

        action = parsed["_action"]

        if action == "ask_user":
            answer = await self._wait_for_user_input(parsed, call_id)
            content = answer if isinstance(answer, str) else answer.get("text", str(answer))
            return fn_name, {"role": "tool", "tool_call_id": call_id, "content": content}

        if action == "confirm_and_execute":
            response = await self._wait_for_user_input(parsed, call_id)
            confirmed = isinstance(response, dict) and response.get("confirmed", False)
            if confirmed:
                retry_args = parsed["_retry_args"]
                retry_result = await ts.invoke(**retry_args)
                return fn_name, {"role": "tool", "tool_call_id": call_id, "content": retry_result}
            else:
                reason = response.get("text", "") if isinstance(response, dict) else str(response)
                cancel_msg = "用户取消了该命令执行。"
                if reason:
                    cancel_msg += f" 原因：{reason}"
                return fn_name, {"role": "tool", "tool_call_id": call_id, "content": cancel_msg}

        if action == "todos_updated":
            todos = parsed.get("todos", [])
            self.todos = todos
            self._save_todos(todos)
            self._event_queue.put_nowait({"type": "todos_updated", "todos": todos})
            msg = "任务列表已更新。"
            return fn_name, {
                "role": "tool",
                "tool_call_id": call_id,
                "content": msg,
            }

        return fn_name, {
            "role": "tool",
            "tool_call_id": call_id,
            "content": result,
        }

    async def _wait_for_user_input(self, action_data: dict, call_id: str) -> object:
        """Pause execution and wait for user input via the actions API."""
        self.state = "waiting_user"
        self.pending_question = action_data

        event = asyncio.Event()
        self.action_waiters[call_id] = event

        try:
            await asyncio.wait_for(event.wait(), self._user_input_timeout)
            return self.action_payloads.pop(call_id, "")
        except TimeoutError:
            if action_data["_action"] == "confirm_and_execute":
                return {"confirmed": False, "text": "超时自动取消"}
            return (
                "[System] 超过 10 分钟未收到用户回应，"
                "该操作已自动取消。请尝试其他方案或跳过此步骤。"
            )
        finally:
            self.state = "idle"
            self.pending_question = None
            self.action_waiters.pop(call_id, None)

    # ── Streaming ReAct loop ───────────────────────────────────────────────

    async def run(self, task_id: str, prompt: str) -> AsyncIterator[dict]:
        cv_token = _file_scope_var.set(self.file_scope)
        config_token = _skill_config_var.set(self._skills_config)
        seq = 0

        def s() -> int:
            nonlocal seq
            seq += 1
            return seq

        stored_events: list[dict] = []

        self.tasks[task_id] = TaskRecord(
            task_id=task_id,
            created_at=datetime.now(UTC).isoformat(),
            task=self._pending_tasks.get(task_id, prompt),
            status="running",
            events=[],
        )

        def emit(event: dict) -> dict:
            stored_events.append(event)
            return event

        try:
            yield emit({"type": "task_started", "task_id": task_id, "seq": s()})
            self.state = "running"

            messages: list[dict] = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": prompt})
            tool_schemas = [t.to_openai_schema() for t in self.tools] or None

            for _ in range(self.max_iterations):
                if task_id in self._cancelled:
                    yield emit({"type": "cancelled", "task_id": task_id, "seq": s()})
                    self.tasks[task_id].status = "cancelled"
                    return

                accumulated_text = ""
                accumulated_thinking = ""
                tool_calls_buf: dict[int, dict] = {}
                finish_reason: str | None = None
                think_parser = _ThinkParser()

                try:
                    async for chunk in stream_chat_completion(
                        llm_config=self.llm_config,
                        messages=messages,
                        tools=tool_schemas,
                    ):
                        if not chunk.get("choices"):
                            continue
                        choice = chunk["choices"][0]
                        finish_reason = choice.get("finish_reason") or finish_reason
                        delta = choice.get("delta", {})

                        # Thinking tokens (Gemini extended thinking / DeepSeek R1 style)
                        if thinking_chunk := (
                            delta.get("reasoning") or delta.get("reasoning_content")
                        ):
                            accumulated_thinking += thinking_chunk

                        if text_chunk := delta.get("content"):
                            text_out, think_out = think_parser.feed(text_chunk)
                            if think_out:
                                accumulated_thinking += think_out
                            if text_out:
                                accumulated_text += text_out
                                yield emit({"type": "text_delta", "content": text_out, "seq": s()})

                        if tc_chunks := delta.get("tool_calls"):
                            _accumulate_tool_calls(tool_calls_buf, tc_chunks)

                except Exception as e:
                    yield emit(
                        {
                            "type": "error",
                            "level": "fatal",
                            "message": f"LLM 调用异常: {e}",
                            "task_id": task_id,
                            "recoverable": False,
                            "seq": s(),
                        }
                    )
                    self.tasks[task_id].status = "error"
                    return

                # Flush any partial <think> tag buffer at stream end
                flush_text, flush_think = think_parser.flush()
                if flush_think:
                    accumulated_thinking += flush_think
                if flush_text:
                    accumulated_text += flush_text
                    yield emit({"type": "text_delta", "content": flush_text, "seq": s()})

                # Emit accumulated thinking before acting on the response
                if accumulated_thinking:
                    yield emit({"type": "thinking", "content": accumulated_thinking, "seq": s()})

                if finish_reason == "tool_calls" or tool_calls_buf:
                    tool_calls_list = [
                        {"id": v["id"], "type": "function", "function": v["function"]}
                        for v in sorted(tool_calls_buf.values(), key=lambda x: x.get("index", 0))
                    ]
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_list,
                        }
                    )

                    for tc in tool_calls_list:
                        yield emit(
                            {
                                "type": "skill_call",
                                "id": tc["id"],
                                "skill": tc["function"]["name"],
                                "args": _safe_json_loads(tc["function"]["arguments"]),
                                "status": "running",
                                "seq": s(),
                            }
                        )

                    results = await asyncio.gather(*(self.exec_tool(tc) for tc in tool_calls_list))

                    for name, tr in results:
                        content = tr["content"]
                        if isinstance(content, list) and any(
                            b.get("type") == "image_url" for b in content
                        ):
                            # OpenAI tool messages only support string content; image_url
                            # blocks must be delivered as a user message so the LLM sees them.
                            text_only = next(
                                (b["text"] for b in content if b.get("type") == "text"), ""
                            )
                            messages.append({**tr, "content": text_only})
                            messages.append({"role": "user", "content": content})
                        else:
                            messages.append(tr)
                        result_preview = (
                            content
                            if isinstance(content, str)
                            else next(
                                (b["text"] for b in content if b.get("type") == "text"),
                                f"[多媒体内容，{len(content)} 个内容块]",
                            )
                        )
                        yield emit(
                            {
                                "type": "skill_result",
                                "id": tr["tool_call_id"],
                                "skill": name,
                                "status": "done",
                                "result": result_preview,
                                "seq": s(),
                            }
                        )

                    # Drain _action side-effect events (e.g. todos_updated)
                    while not self._event_queue.empty():
                        side_event = self._event_queue.get_nowait()
                        side_event["seq"] = s()
                        yield emit(side_event)

                elif finish_reason in _DONE_REASONS or accumulated_text:
                    if not accumulated_text and finish_reason in _DONE_REASON_NOTES:
                        accumulated_text = _DONE_REASON_NOTES[finish_reason]
                        yield emit({"type": "text_delta", "content": accumulated_text, "seq": s()})
                    messages.append({"role": "assistant", "content": accumulated_text})
                    yield emit({"type": "done", "task_id": task_id, "summary": "", "seq": s()})
                    self.tasks[task_id].status = "done"
                    self.tasks[task_id].events = stored_events
                    return

                else:
                    # finish_reason is null/unexpected with no content or tool calls.
                    # Break immediately to avoid re-sending the same payload in an
                    # infinite loop (root cause of "24 calls, 766 tokens, no result").
                    yield emit(
                        {
                            "type": "error",
                            "level": "warning",
                            "message": (
                                f"LLM 返回了无法处理的响应状态"
                                f"（finish_reason={finish_reason!r}，无内容，无工具调用），"
                                "已中止以避免无限循环。"
                            ),
                            "task_id": task_id,
                            "recoverable": False,
                            "seq": s(),
                        }
                    )
                    self.tasks[task_id].status = "error"
                    return

            yield emit(
                {
                    "type": "error",
                    "level": "warning",
                    "message": f"任务已强制终止：超过最大迭代次数 ({self.max_iterations})",
                    "task_id": task_id,
                    "recoverable": False,
                    "seq": s(),
                }
            )
            self.tasks[task_id].status = "error"

        finally:
            self.state = "idle"
            if task_id in self.tasks:
                self.tasks[task_id].events = stored_events
            _skill_config_var.reset(config_token)
            _file_scope_var.reset(cv_token)

    async def run_turn(
        self,
        session_id: str,
        turn_id: str,
        user_message: str,
        history: list[dict],
    ) -> AsyncIterator[dict]:
        cv_token = _file_scope_var.set(self.file_scope)
        config_token = _skill_config_var.set(self._skills_config)
        key = (session_id, turn_id)
        seq = 0

        def s() -> int:
            nonlocal seq
            seq += 1
            return seq

        try:
            yield {"type": "task_started", "task_id": turn_id, "seq": s()}
            self.state = "running"

            messages: list[dict] = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})
            tool_schemas = [t.to_openai_schema() for t in self.tools] or None

            for _ in range(self.max_iterations):
                if key in self._cancelled_turns:
                    yield {"type": "cancelled", "task_id": turn_id, "seq": s()}
                    return

                accumulated_text = ""
                accumulated_thinking = ""
                tool_calls_buf: dict[int, dict] = {}
                finish_reason: str | None = None
                think_parser = _ThinkParser()

                try:
                    async for chunk in stream_chat_completion(
                        llm_config=self.llm_config,
                        messages=messages,
                        tools=tool_schemas,
                    ):
                        if not chunk.get("choices"):
                            continue
                        choice = chunk["choices"][0]
                        finish_reason = choice.get("finish_reason") or finish_reason
                        delta = choice.get("delta", {})

                        # Thinking tokens (Gemini extended thinking / DeepSeek R1 style)
                        if thinking_chunk := (
                            delta.get("reasoning") or delta.get("reasoning_content")
                        ):
                            accumulated_thinking += thinking_chunk

                        if text_chunk := delta.get("content"):
                            text_out, think_out = think_parser.feed(text_chunk)
                            if think_out:
                                accumulated_thinking += think_out
                            if text_out:
                                accumulated_text += text_out
                                yield {"type": "text_delta", "content": text_out, "seq": s()}

                        if tc_chunks := delta.get("tool_calls"):
                            _accumulate_tool_calls(tool_calls_buf, tc_chunks)

                except Exception as e:
                    yield {
                        "type": "error",
                        "level": "fatal",
                        "message": f"LLM 调用异常: {e}",
                        "task_id": turn_id,
                        "recoverable": False,
                        "seq": s(),
                    }
                    return

                # Flush any partial <think> tag buffer at stream end
                flush_text, flush_think = think_parser.flush()
                if flush_think:
                    accumulated_thinking += flush_think
                if flush_text:
                    accumulated_text += flush_text
                    yield {"type": "text_delta", "content": flush_text, "seq": s()}

                # Emit accumulated thinking before acting on the response
                if accumulated_thinking:
                    yield {"type": "thinking", "content": accumulated_thinking, "seq": s()}

                if finish_reason == "tool_calls" or tool_calls_buf:
                    tool_calls_list = [
                        {"id": v["id"], "type": "function", "function": v["function"]}
                        for v in sorted(tool_calls_buf.values(), key=lambda x: x.get("index", 0))
                    ]
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_list,
                        }
                    )

                    for tc in tool_calls_list:
                        yield {
                            "type": "skill_call",
                            "id": tc["id"],
                            "skill": tc["function"]["name"],
                            "args": _safe_json_loads(tc["function"]["arguments"]),
                            "status": "running",
                            "seq": s(),
                        }

                    results = await asyncio.gather(*(self.exec_tool(tc) for tc in tool_calls_list))

                    for name, tr in results:
                        content = tr["content"]
                        if isinstance(content, list) and any(
                            b.get("type") == "image_url" for b in content
                        ):
                            # OpenAI tool messages only support string content; image_url
                            # blocks must be delivered as a user message so the LLM sees them.
                            text_only = next(
                                (b["text"] for b in content if b.get("type") == "text"), ""
                            )
                            messages.append({**tr, "content": text_only})
                            messages.append({"role": "user", "content": content})
                        else:
                            messages.append(tr)
                        result_preview = (
                            content
                            if isinstance(content, str)
                            else next(
                                (b["text"] for b in content if b.get("type") == "text"),
                                f"[多媒体内容，{len(content)} 个内容块]",
                            )
                        )
                        yield {
                            "type": "skill_result",
                            "id": tr["tool_call_id"],
                            "skill": name,
                            "status": "done",
                            "result": result_preview,
                            "seq": s(),
                        }

                    while not self._event_queue.empty():
                        side_event = self._event_queue.get_nowait()
                        side_event["seq"] = s()
                        yield side_event

                elif finish_reason in _DONE_REASONS or accumulated_text:
                    if not accumulated_text and finish_reason in _DONE_REASON_NOTES:
                        accumulated_text = _DONE_REASON_NOTES[finish_reason]
                        yield {"type": "text_delta", "content": accumulated_text, "seq": s()}
                    messages.append({"role": "assistant", "content": accumulated_text})
                    yield {"type": "done", "task_id": turn_id, "summary": "", "seq": s()}
                    return

                else:
                    yield {
                        "type": "error",
                        "level": "warning",
                        "message": (
                            f"LLM 返回了无法处理的响应状态"
                            f"（finish_reason={finish_reason!r}，无内容，无工具调用），"
                            "已中止以避免无限循环。"
                        ),
                        "task_id": turn_id,
                        "recoverable": False,
                        "seq": s(),
                    }
                    return

            yield {
                "type": "error",
                "level": "warning",
                "message": f"任务已强制终止：超过最大迭代次数 ({self.max_iterations})",
                "task_id": turn_id,
                "recoverable": False,
                "seq": s(),
            }

        finally:
            self.state = "idle"
            self._pending_turns.pop(key, None)
            _skill_config_var.reset(config_token)
            _file_scope_var.reset(cv_token)
