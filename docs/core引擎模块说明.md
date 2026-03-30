# Core 引擎模块说明

`src/agentos/core/` 包含框架运行时依赖的所有无状态逻辑：配置解析、Skill 发现与加载、ReAct Agent 循环、LLM 调用、文件访问控制、Git Skill 安装、版本锁定和权限校验。

**依赖方向规则**：`cli` 和 `server` 可以 import `core`，`core` 不得 import `cli` 或 `server`。

## 模块一览

| 文件 | 职责 |
|------|------|
| `project_config.py` | 解析 `agent.toml` → `ProjectConfig` dataclass |
| `skill_loader.py` | 发现所有 Skills（CLI 用）和按声明加载 Skills（运行时）|
| `tool.py` | `@tool` 装饰器，生成 `ToolSpec` 对象 |
| `llm.py` | 异步 LiteLLM 封装，返回 OpenAI 格式 dict |
| `runner.py` | `AgentRunner`：异步 ReAct 循环，并行执行 tool_calls |
| `file_scope.py` | `FileScope`：per-project 文件路径访问控制 |
| `lock_manager.py` | `LockManager`：读写 `agent-lock.toml` |
| `git_installer.py` | `GitInstaller`：clone、校验、缓存 Git Skills |
| `permission_checker.py` | `PermissionChecker`：运行时权限校验 |

---

## project_config.py — ProjectConfig

`ProjectConfig` 是由 `ProjectConfig.from_toml(path)` 填充的 dataclass，构造后不可变。所有其他模块通过构造函数参数接收它。

### 字段说明

| 字段 | 类型 | 默认值 | 对应 agent.toml |
|------|------|--------|-----------------|
| `name` | `str` | `""` | `[project] name` |
| `version` | `str` | `"0.1.0"` | `[project] version` |
| `llm_model` | `str` | `""` | `[llm] model` |
| `llm_base_url` | `str` | `""` | `[llm] base_url` |
| `agent_type` | `str` | `"react"` | `[agent] type` |
| `max_iterations` | `int` | `20` | `[agent] max_iterations` |
| `skills` | `dict[str, dict]` | `{}` | `[skills]` 表 |
| `scope_allow` | `list[str]` | `["./"]` | `[scope] allow` |
| `scope_deny` | `list[str]` | `[]` | `[scope] deny` |

### 使用示例

```python
from agentos.core.project_config import ProjectConfig

config = ProjectConfig.from_toml(Path("agent.toml"))
print(config.llm_model)   # "gemini-2.0-flash"
print(config.skills)      # {"file_reader": {"source": "builtin"}, ...}
```

### 新增字段步骤

1. 在 `@dataclass` 中添加有默认值的字段
2. 在 `from_toml` 中从 `data.get(...)` 解析
3. 如需在新项目中出现，更新 `cli/init_cmd.py` 中的 `agent.toml` 模板

---

## tool.py — ToolSpec 与 @tool 装饰器

`ToolSpec` 是可调用工具的规范表示，包含名称、docstring 描述、Pydantic 生成的 JSON Schema 和原始 Python callable。

### @tool 装饰器用法

```python
from agentos.core.tool import tool

@tool
def read_file(file_path: str) -> str:
    """读取项目目录内的文本文件内容。"""
    ...
```

装饰器执行过程：
1. 通过 `inspect.signature` 检查函数签名
2. 从参数注解和默认值构建 Pydantic model
3. 提取 JSON Schema
4. 返回 `ToolSpec` 实例（替换原始函数）

### ToolSpec 接口

```python
spec.name                  # str — 函数名（可通过 agent.toml 别名覆盖）
spec.description           # str — docstring
spec.parameters            # dict — JSON Schema（传给 LLM 的 tool 定义）
spec.to_openai_schema()    # -> dict，兼容 OpenAI tools[] 参数
await spec.invoke(**kwargs) # Pydantic 验证参数后调用函数；支持 async
```

### 注意

`SkillLoader` 通过 `isinstance(obj, ToolSpec)` 识别工具。不要使用 LangChain 的 `@tool`，它产生不同类型。

---

## llm.py — LLM 调用

两个公开异步函数，都是 `litellm.acompletion` 的薄封装。

### chat_completion（非流式）

```python
from agentos.core.llm import chat_completion

response = await chat_completion(
    model="gemini-2.0-flash",
    messages=[{"role": "user", "content": "Hello"}],
    tools=[...],
    api_key="...",
    base_url="https://...",
    temperature=0.2,
)
# response["choices"][0]["message"]["content"]
# response["choices"][0]["message"]["tool_calls"]
```

### stream_chat_completion（流式）

```python
from agentos.core.llm import stream_chat_completion

async for chunk in stream_chat_completion(model=..., messages=...):
    delta = chunk["choices"][0]["delta"]
    # delta["content"] 或 delta["tool_calls"]
```

### LiteLLM 模型字符串路由

| 模型字符串 | 路由到 |
|-----------|--------|
| `gpt-4o` | OpenAI |
| `claude-3-5-sonnet-20241022` | Anthropic |
| `gemini-2.0-flash` | Google Gemini |
| `ollama/mistral` | 本地 Ollama |
| `openai/my-model` | 自定义 OpenAI 兼容端点 |

---

## runner.py — AgentRunner

自定义 ReAct（推理+行动）循环，无 LangChain 依赖。

### 构造函数

```python
runner = AgentRunner(
    model="gemini-2.0-flash",
    api_key="...",
    base_url="...",
    tools=[list_of_tool_specs],
    max_iterations=20,
    temperature=0.2,
)
```

### run() — 异步生成器

```python
async for event in runner.run(task_id="task_abc123", prompt="分析 data.csv"):
    print(event)
```

生成的 SSE 事件 dict：

| `type` | 触发时机 | 关键字段 |
|--------|---------|---------|
| `skill_call` | 工具执行前 | `id`, `skill`, `args`, `status="running"` |
| `skill_result` | 工具执行后 | `id`, `skill`, `status="done"`, `result` |
| `text` | LLM 最终答复 | `content` |
| `done` | 任务完成 | `task_id`, `summary` |
| `cancelled` | 已调用 cancel() | `task_id` |
| `error` | LLM 或工具异常 | `data.message` |

### 并行执行

LLM 一次返回多个 `tool_calls` 时，通过 `asyncio.gather` 并发执行所有工具。Skills 必须线程/并发安全，不能共享可变状态。

### 取消

```python
runner.cancel("task_abc123")
```

取消在 LLM 调用之间生效，不会中断正在执行的工具。

### 接入服务端

目前 `server/app.py` 使用 `StubEngine`，接入真实 Runner 的方法见 [server-api.md](server-api.md)。

---

## skill_loader.py — SkillLoader

### 三层搜索来源（优先级由低到高）

1. **builtin** — `src/agentos/builtin_skills/`（随包分发）
2. **全局旧版** — `~/.agentos/skills/<name>/`（向后兼容）
3. **全局版本化缓存** — `~/.agentos/skills/<host>/<user>/<repo>/<tag>/`
4. **本地** — `<project_dir>/skills/`（最高优先级，可覆盖同名 builtin）

### 入口点解析顺序

`_find_skill_entry(path)` 按以下顺序解析：
1. 路径是 `.py` 文件 → 直接使用
2. 目录含 `__init__.py` → 使用它
3. 目录含 `skill.py` → 使用它

### 别名与覆盖

`agent.toml` 的 key 作为工具别名。加载后 `loaded.name` 被设为 key 名。若声明了 `override.prompt`，该 Skill 下所有 `ToolSpec` 的 description 会被替换。

### SkillInfo vs LoadedSkill

- `SkillInfo` — 轻量元数据，用于 CLI 展示（name、source、version 等）
- `LoadedSkill` — 运行时对象，包含实际 `tool_functions: list[ToolSpec]`（通过 `importlib` 加载）

---

## file_scope.py — FileScope

执行 `agent.toml` 中 `[scope]` 配置。所有涉及文件系统的内置 Skill 在操作前都调用 `scope.check_access(path)`。

### 访问控制算法（按优先级）

1. 拒绝绝对路径（Windows `C:\` 和 Unix `/` 开头）
2. 拒绝符号链接
3. 拒绝解析后跳出项目目录的路径（路径遍历攻击）
4. 若解析后相对路径匹配任意 `deny` glob → 拒绝
5. 若解析后相对路径匹配任意 `allow` glob → 允许
6. 默认：拒绝

### Skill 中的使用方式

```python
from agentos.builtin_skills._common import get_file_scope

scope = get_file_scope()   # 未注入时返回 None（无限制）
if scope is not None:
    allowed, reason = scope.check_access("data/file.csv")
    if not allowed:
        return f"访问被拒绝：{reason}"
```

### AgentRunner 注入方式

```python
import agentos.builtin_skills._common as _common
_common.get_file_scope = lambda: FileScope(
    project_dir=project_dir,
    allow=config.scope_allow,
    deny=config.scope_deny,
)
```

---

## lock_manager.py — LockManager

使用 `tomlkit`（保留注释和格式）管理 `agent-lock.toml`。

### LockEntry 字段

| 字段 | 类型 | 用途 |
|------|------|------|
| `git` | `str` | 原始 Git URL |
| `tag` | `str` | agent.toml 中声明的 tag |
| `commit` | `str` | 安装时校验的实际 commit hash |
| `resolved_path` | `str` | 相对缓存路径 |
| `approved_permissions` | `list[str]` | 用户已审批的权限列表 |

### 主要方法

```python
manager = LockManager(Path("agent-lock.toml"))
entry = manager.get_lock("web_search")       # LockEntry | None
manager.set_lock("web_search", entry)        # upsert
manager.remove_lock("web_search")            # 删除
manager.save()                               # 写入磁盘（变更后必须调用）
new_perms = manager.get_new_permissions("web_search", requested)  # 求差集
```

使用 `tomlkit` 而非 `tomllib` 的原因：`tomllib` 只读；`tomlkit` 支持保真读写，`agent-lock.toml` 需要提交到版本控制，最小化 diff。

---

## git_installer.py — GitInstaller

将 Git 托管的 Skills 安装到 `~/.agentos/skills/` 全局版本化缓存。

### 缓存路径结构

```
~/.agentos/skills/
└── github.com/
    └── my-org/
        └── web-search/
            ├── v1.0.0/        ← git clone --depth 1 --branch v1.0.0
            │   ├── skill.toml
            │   └── skill.py
            └── v1.1.0/
```

### 主要方法

```python
installer = GitInstaller()
installer.is_cached(git_url, tag)              # 是否已缓存
cache_path, commit_hash = installer.clone(git_url, tag)  # 克隆
manifest = installer.read_manifest(cache_path)
permissions = installer.extract_permissions(manifest)
# 返回如 ["network", "env_vars:TAVILY_API_KEY"]
```

### Commit Hash 校验

重新安装已有锁定记录的 tag 时，`skill_cmd.py` 会比对 `clone()` 返回的 commit 与 `lock_entry.commit`。不一致说明远端 tag 被强推（潜在供应链攻击），CLI 以非零码退出。

---

## permission_checker.py — PermissionChecker

### 权限字符串格式

| 格式 | 含义 |
|------|------|
| `"file_read"` | 读取文件 |
| `"file_write"` | 写入文件 |
| `"network"` | 发出 HTTP 请求 |
| `"shell"` | 执行 shell 命令 |
| `"env_vars:MY_VAR"` | 读取指定环境变量 |

### check_runtime()

```python
checker = PermissionChecker(lock_manager)
result = checker.check_runtime(
    skill_name="web_search",
    requested_permissions=["network", "env_vars:TAVILY_API_KEY"],
    source="git",
)
if not result.allowed:
    raise PermissionError(result.message)
```

- `builtin` 和 `local` 来源始终允许
- `git` 来源只有每个请求的权限都在 `approved_permissions` 中才允许

---

## 测试模式

### 用 tmp_path 隔离

```python
def test_something(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    config = ProjectConfig(skills={"my_skill": {"source": "builtin"}})
    loader = SkillLoader(project_dir, config)
    loader.global_skills_dir = tmp_path / "fake_global"  # 防止污染真实缓存
```

### 测试 AgentRunner 事件

```python
@pytest.mark.anyio
async def test_runner_yields_text(monkeypatch):
    import agentos.core.llm as llm_mod
    async def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "Hello!", "tool_calls": None}}]}
    monkeypatch.setattr(llm_mod, "chat_completion", fake_completion)
    # ... 断言事件序列
```
