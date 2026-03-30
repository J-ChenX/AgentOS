# agent.toml 配置参考

每个 Agent 项目根目录下必须有 `agent.toml`，是所有配置的唯一真相来源（Truth Source）。

## 完整示例

```toml
[project]
name = "my-agent"
version = "0.1.0"

[llm]
model = "gemini-2.0-flash"       # 任意 LiteLLM model 字符串
base_url = "https://..."         # 可选，自定义 API 端点

[agent]
type = "react"                   # 目前仅支持 "react"
max_iterations = 20

[scope]
allow = ["./"]                   # FileScope 允许访问的 glob 路径
deny = [".env", "*.key"]         # deny 优先级高于 allow

[skills]
# 内置 Skill（随 agentos 包分发）
file_reader = { source = "builtin" }

# 本地 Skill（项目 skills/ 目录）
hello = { path = "./skills/hello.py" }

# Git 托管 Skill（安装到 ~/.agentos/skills/）
web_search = { git = "https://github.com/org/web-search.git", tag = "v1.2.0" }

# Soft Eject：覆盖 prompt，无需复制源码
file_reader = { source = "builtin", override = { prompt = "Always respond in English." } }
```

## 字段说明

### `[project]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Agent 项目名称 |
| `version` | string | 项目版本，默认 `"0.1.0"` |

### `[llm]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | string | LiteLLM model 字符串（如 `gpt-4o`、`claude-3-5-sonnet-20241022`）|
| `base_url` | string | 可选，自定义端点（Ollama、本地代理等）|

### `[agent]`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"react"` | Agent 类型，当前仅 `react` |
| `max_iterations` | int | `20` | ReAct 循环最大轮次 |

### `[scope]`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allow` | list[str] | `["./"]` | FileScope 允许的路径 glob |
| `deny` | list[str] | `[]` | 明确拒绝的路径（优先级更高）|

### `[skills]`

键名作为 LLM tool name（别名）。值为 Skill 来源声明：

| 来源类型 | 写法 | 说明 |
|----------|------|------|
| 内置 | `{ source = "builtin" }` | 框架自带 Skills |
| 本地路径 | `{ path = "./skills/foo.py" }` | 项目内 Skill 文件 |
| Git | `{ git = "https://...", tag = "v1.0" }` | 远程 Git 仓库 |
| override | 任意来源 + `override = {...}` | Soft Eject，覆盖部分配置 |

## agent-lock.toml

由 `LockManager` 自动维护，**不要手动编辑**，需提交到版本控制。

记录 Git Skills 的 commit hash 和已审批权限：

```toml
[meta]
generated_at = "2026-03-24T10:00:00+00:00"
agentos_version = "0.1.0"

[locks.web_search]
git = "https://github.com/org/web-search.git"
tag = "v1.2.0"
commit = "abc123def456..."
resolved_path = "github.com/org/web-search/v1.2.0"
approved_permissions = ["network", "env_vars:TAVILY_API_KEY"]
```
