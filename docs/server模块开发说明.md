# Server 模块开发说明

`src/agentos/server/` 是 FastAPI 应用，将 Agent 后端以 HTTP API 形式暴露。Web UI（React）通过此 API 通信。开发模式下 Vite 在独立端口运行，生产模式下静态文件从 `_web_assets/` 目录提供。

## 目录结构

```
server/
├── app.py           应用工厂 — create_app(dev_mode) + 静态文件挂载
├── models.py        Pydantic 请求/响应模型
├── sse.py           sse_response() — 封装 sse-starlette EventSourceResponse
├── stub_engine.py   StubEngine — 确定性 demo 引擎，回放固定事件序列
└── routes/
    ├── tasks.py     POST/GET /api/tasks，SSE 流
    ├── skills.py    GET/PATCH /api/skills
    ├── files.py     GET /api/files
    ├── config.py    GET/PATCH /api/config
    └── actions.py   POST /api/actions/{action_id}
```

---

## app.py — 应用工厂

`create_app(dev_mode=False)` 是唯一入口，执行：

1. 实例化引擎（当前为 `StubEngine`，生产替换为 `AgentRunner`）
2. 添加 CORS 中间件（开发用通配符；生产应限制 origin）
3. 在 `/api` 前缀下注册所有路由
4. 非 dev 模式且 `_web_assets/` 非空时，挂载 React 构建产物（HTML fallback）

模块底部的 `app = create_app()` 是 uvicorn 的引用入口。

### 替换引擎（StubEngine → AgentRunner）

```python
# app.py 中的 create_engine()
from agentos.core.runner import AgentRunner
from agentos.core.project_config import ProjectConfig
from agentos.core.skill_loader import SkillLoader
from pathlib import Path

def create_engine(dev_mode: bool = False):
    project_dir = Path.cwd()
    config = ProjectConfig.from_toml(project_dir / "agent.toml")
    loader = SkillLoader(project_dir, config)
    loaded_skills = loader.load_project_skills()
    tools = [t for ls in loaded_skills for t in ls.tool_functions]
    return AgentRunner(
        model=config.llm_model,
        base_url=config.llm_base_url or None,
        tools=tools,
        max_iterations=config.max_iterations,
    )
```

`AgentRunner` 已满足引擎契约：`run(task_id, task)` 异步生成器 + `cancel(task_id)` 方法，替换后无需修改路由文件。

---

## SSE 协议 — sse.py

`sse_response(request, event_stream)` 将 `AsyncIterator[dict]` 封装为 `EventSourceResponse`，每个 dict 变成一条 SSE 事件：

```
id: <seq>
data: <json-encoded event dict>
```

`seq` 字段用作 SSE `id`，前端断线重连时发送 `Last-Event-ID`，服务端据此回放丢失事件。每 15 秒发送 ping 保活。

### SSE 事件类型

| `type` | 来源 | 说明 |
|--------|------|------|
| `task_started` | 引擎 | 任务开始时第一个事件 |
| `thinking` | 引擎 | LLM 推理中 |
| `skill_call` | AgentRunner | 工具调用开始 |
| `skill_result` | AgentRunner | 工具调用完成 |
| `text` | AgentRunner | LLM 最终文本回复 |
| `component` | Agent Skills | 富 UI 组件（表格、图表等）|
| `component_delta` | Agent Skills | 组件增量更新 |
| `action_required` | Agent Skills | 请求用户交互（确认框、表单）|
| `done` | 引擎 | 任务成功完成 |
| `cancelled` | 引擎 | 任务已取消 |
| `error` | 引擎/AgentRunner | 致命错误 |

完整类型定义见 `web/src/types/index.ts`。

### 断线重连

`routes/tasks.py` 通过 `Last-Event-ID` 头处理重连：已完成的任务从指定 seq 回放剩余事件；仍在运行的任务接入实时流。

---

## Pydantic 模型 — models.py

所有请求体和响应形状使用 Pydantic v2 `BaseModel`。模型统一放在 `models.py`，不要内联在路由文件中。

| 模型 | 方向 | 使用路由 |
|------|------|---------|
| `TaskCreate` | 请求 | `POST /api/tasks` |
| `TaskCreated` | 响应 | `POST /api/tasks` |
| `ActionSubmit` | 请求 | `POST /api/actions/{id}` |
| `SkillToggle` | 请求 | `PATCH /api/skills/{name}` |
| `SkillInfo` | 响应 | `GET /api/skills` |
| `ConfigPatch` | 请求 | `PATCH /api/config` |
| `AgentConfigModel` | 响应 | `GET /api/config` |
| `FileNodeModel` | 响应 | `GET /api/files` |
| `TaskRecord` | 内部+响应 | `GET /api/tasks/{id}` |

`TaskRecord` 保存任务所有事件（用于断线回放）：

```python
class TaskRecord(BaseModel):
    task_id: str
    created_at: str          # ISO 8601 UTC
    task: str                # 原始 prompt
    status: Literal["running", "done", "error", "cancelled"]
    events: list[dict]       # 所有 SSE 事件（用于回放）
    summary: str | None
```

---

## 路由文件 — routes/

每个路由文件导出单一工厂函数 `create_*_router(engine?)` 返回 `APIRouter`。此模式便于测试：实例化新引擎，传入工厂，挂载路由，对真实 ASGI app 测试。

### routes/tasks.py — 任务生命周期

两步式任务流程：

1. `POST /api/tasks` — 创建 task_id 并注册 prompt，返回 `{"task_id": "task_abc123"}`
2. `GET /api/tasks/{task_id}/stream` — 建立 SSE 连接，前端在第 1 步后立即连接
3. `POST /api/tasks/{task_id}/cancel` — 向引擎发送取消信号
4. `GET /api/tasks` — 历史任务列表
5. `GET /api/tasks/{task_id}` — 单个任务详情

### routes/skills.py

当前使用模块级 `_STUB_SKILLS`。接入真实 `SkillLoader` 时，替换为 `loader.load_project_skills()` 并适配 `SkillInfo` 响应模型。

### routes/config.py

当前返回 `_STUB_CONFIG`。接入真实配置时，GET 从 `agent.toml` 读取，PATCH 用 `tomlkit` 写入。

### routes/files.py

当前返回 stub 文件树。生产实现应遍历项目目录并遵守 `FileScope` 规则。

### routes/actions.py

接收 `POST /api/actions/{action_id}` 的 payload，调用 `engine.submit_action(action_id, payload)`。用于 `action_required` 事件触发的 UI 交互（确认框、表单等）。引擎为每个 `action_id` 持有一个 `asyncio.Event`，等待前端提交后唤醒对应协程。

---

## StubEngine — stub_engine.py

自包含的 demo 引擎，每次任务回放固定事件序列，是当前唯一接入 `create_app()` 的引擎。

Demo 事件序列：
```
task_started → thinking → skill_call → skill_result → text → component → component_delta → done
```

覆盖所有前端处理的事件类型，适合无真实 LLM 时的 UI 开发。

---

## 新增路由规范

### 步骤 1：添加 Pydantic 模型

```python
# models.py
class MyNewRequest(BaseModel):
    param: str

class MyNewResponse(BaseModel):
    result: str
```

### 步骤 2：创建路由工厂

```python
# routes/my_resource.py
from fastapi import APIRouter
from agentos.server.models import MyNewRequest, MyNewResponse

def create_my_resource_router() -> APIRouter:
    router = APIRouter()

    @router.get("/my-resource")
    async def get_resource():
        return MyNewResponse(result="hello")

    @router.post("/my-resource")
    async def create_resource(body: MyNewRequest):
        return MyNewResponse(result=body.param.upper())

    return router
```

### 步骤 3：在 app.py 注册

```python
from agentos.server.routes.my_resource import create_my_resource_router

app.include_router(create_my_resource_router(), prefix="/api")
```

### 步骤 4：编写集成测试

```python
# tests/server/test_my_resource.py
@pytest.mark.anyio
async def test_get_resource(client):
    resp = await client.get("/api/my-resource")
    assert resp.status_code == 200
    assert resp.json()["result"] == "hello"
```

`client` fixture 由 `tests/server/conftest.py` 提供，基于 `ASGITransport(app=create_app())`。

---

## 新增 SSE 事件类型规范

1. 在 `server/models.py` 中定义事件 dict 结构（可选，用于文档）
2. 在引擎或 Skill 中用标准格式（含 `type` 和 `seq` 字段）emit 事件
3. 在 `web/src/types/index.ts` 添加 TypeScript 接口
4. 在 `web/src/components/events/EventRenderer.tsx` 处理新类型

---

## 测试

```bash
python -m pytest tests/server/ -v
python -m pytest tests/server/ -v -s   # 含输出，适合 SSE 调试
```

每个测试获得新的 `create_app()` 实例，`StubEngine` 也是全新的，测试完全隔离，不调用真实 LLM。

### 测试 SSE 流

```python
@pytest.mark.anyio
async def test_task_stream(client):
    resp = await client.post("/api/tasks", json={"task": "test"})
    task_id = resp.json()["task_id"]

    events = []
    async with client.stream("GET", f"/api/tasks/{task_id}/stream") as r:
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert events[-1]["type"] == "done"
```
