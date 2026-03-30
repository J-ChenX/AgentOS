# AgentOS

**可复用 AI Agent 框架** — 在任意目录一条命令拉起对话式 AI 智能体，通过 Web UI 交互。

```bash
pip install agentos
cd my-project
agentos
```

---

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [项目配置](#项目配置-agenttoml)
- [Skills 系统](#skills-系统)
- [CLI 命令](#cli-命令)
- [Web UI](#web-ui)
- [API 参考](#api-参考)
- [开发框架本身](#开发框架本身)
- [文档索引](#文档索引)

---

## 特性

- **零配置启动** — 项目根目录放一个 `agent.toml`，运行 `agentos` 即可
- **对话式 Web UI** — 内置 React 界面，支持实时 SSE 流式输出
- **Skills 插件系统** — 三种来源（内置 / 本地 / Git 托管），声明即加载
- **并行工具执行** — LLM 一次返回多个 tool_calls 时自动并发执行
- **文件访问控制** — `FileScope` 严格限制 Skill 可访问的路径范围
- **Git Skill 安全审计** — commit hash 锁定 + 权限审批，防供应链攻击
- **多模型支持** — 通过 LiteLLM 接入 OpenAI、Anthropic、Gemini、Ollama 等

---

## 快速开始

### 安装

```bash
pip install agentos
```

### 创建 Agent 项目

```bash
agentos init my-agent
cd my-agent
```

生成的目录结构：

```
my-agent/
├── agent.toml        # 项目配置
├── skills/
│   └── hello.py      # 示例 Skill
└── .env              # API 密钥（不提交 VCS）
```

### 配置 API 密钥

编辑 `.env`：

```env
OPENAI_API_KEY=sk-...
# 或
ANTHROPIC_API_KEY=sk-ant-...
# 或
GEMINI_API_KEY=...
```

### 启动

```bash
agentos run
# 浏览器访问 http://localhost:8000
```

---

## 项目配置 agent.toml

每个 Agent 项目通过 `agent.toml` 配置，是所有设置的唯一真相来源。

```toml
[project]
name = "my-agent"
version = "0.1.0"

[llm]
model = "gpt-4o"           # 任意 LiteLLM 模型字符串
base_url = ""              # 可选，自定义 API 端点（Ollama 等）

[agent]
type = "react"             # 目前支持 "react"
max_iterations = 20        # ReAct 最大循环轮次

[scope]
allow = ["./"]             # Skill 可访问的路径（glob）
deny = [".env", "*.key"]   # 明确拒绝（优先级更高）

[skills]
file_reader = { source = "builtin" }   # 内置 Skill
my_tool = { path = "./skills/my_tool.py" }  # 本地 Skill
```

完整字段说明见 [docs/agent配置参考.md](docs/agent配置参考.md)。

---

## Skills 系统

Skill 是用 `@tool` 装饰的 Python 函数，AgentOS 自动将其注册为 LLM 工具。

### 编写一个 Skill

```python
# skills/search.py
from agentos.core.tool import tool

@tool
def search_docs(query: str, limit: int = 5) -> str:
    """在项目文档中搜索相关内容，返回匹配的段落。"""
    # ... 实现搜索逻辑
    return results
```

在 `agent.toml` 中声明：

```toml
[skills]
search_docs = { path = "./skills/search.py" }
```

### 三种 Skill 来源

| 来源 | 声明方式 | 说明 |
|------|---------|------|
| 内置 | `{ source = "builtin" }` | 随框架分发，无需安装 |
| 本地 | `{ path = "./skills/foo.py" }` | 项目内文件，直接引用 |
| Git | `{ git = "https://...", tag = "v1.0" }` | 远程仓库，安装到全局缓存 |

### 内置 Skills

| Skill | 功能 |
|-------|------|
| `file_reader` | 读取项目文件（受 FileScope 保护）|
| `web_search` | 网页搜索（需配置 `TAVILY_API_KEY`）|
| `system_shell` | 执行 shell 命令（含危险命令拦截）|

Skills 开发完整规范见 [docs/Skills开发规范.md](docs/Skills开发规范.md)。

---

## CLI 命令

```bash
# 项目管理
agentos                      # 智能入口：有 agent.toml 则启动，否则引导初始化
agentos init <name>          # 创建新 Agent 项目
agentos run                  # 启动服务（生产模式，http://localhost:8000）
agentos run --dev            # 开发模式（后端 hot-reload）
agentos run --port 9000      # 指定端口
agentos version              # 查看版本

# Skill 管理（需在含 agent.toml 的目录下执行）
agentos skill list           # 列出所有可用 Skills
agentos skill add <name>     # 添加内置 Skill 到 agent.toml
agentos skill add <name> --git <url> --tag <tag>  # 添加 Git Skill 并安装
agentos skill install        # 安装 agent.toml 中所有 Git Skills
agentos skill update <name>  # 更新 Skill 版本
agentos skill remove <name>  # 移除 Skill
agentos skill info <name>    # 查看 Skill 详情（来源、版本、权限）
agentos skill eject <name>   # 将 Skill 复制到本地（脱离自动更新）
```

---

## Web UI

启动后访问 `http://localhost:8000`，界面包含可自由分栏的面板：

| 面板 | 功能 |
|------|------|
| **Chat** | 主对话区，实时显示 LLM 推理过程和 Skill 调用结果 |
| **Skills** | 查看和启用/禁用当前项目的 Skills |
| **Files** | 浏览项目文件树 |
| **History** | 查看历史任务记录 |
| **Config** | 在线编辑 agent.toml 配置 |

### 开发模式（前后端分离）

```bash
# Terminal 1 — 前端 HMR（http://localhost:6493）
cd web && npm run dev

# Terminal 2 — 后端（http://localhost:8000）
agentos run --dev --port 8000

# 浏览器访问 http://localhost:6493?adapter=web
```

---

## API 参考

所有接口以 `/api` 为前缀，返回 JSON。

### 任务

```
POST   /api/tasks                     创建任务
                                      Body: { "task": "分析这份报告" }
                                      返回: { "task_id": "task_abc123" }

GET    /api/tasks/{task_id}/stream    SSE 流式获取执行事件
POST   /api/tasks/{task_id}/cancel    取消任务
GET    /api/tasks                     历史任务列表
GET    /api/tasks/{task_id}           任务详情
```

### SSE 事件类型

```
task_started  → 任务开始
thinking      → LLM 推理中
skill_call    → Skill 调用开始 { skill, args }
skill_result  → Skill 调用完成 { skill, result }
text          → LLM 文本回复
component     → 富 UI 组件（表格/图表/表单等）
done          → 任务完成
error         → 发生错误
cancelled     → 任务已取消
```

### 其他接口

```
GET    /api/skills           Skill 列表
PATCH  /api/skills/{name}    启用/禁用 Skill
GET    /api/files            文件树
GET    /api/config           读取配置
PATCH  /api/config           更新配置
POST   /api/actions/{id}     提交 UI 交互结果
```

完整服务端说明见 [docs/server模块开发说明.md](docs/server模块开发说明.md)。

---

## 开发框架本身

### 环境搭建

```bash
git clone <repo>
cd Agent
pip install -e ".[dev]"   # 安装框架（可编辑模式）
pnpm install               # 安装前端依赖

# 首次启动前，需创建一个 Agent 项目作为开发入口
agentos init my_agent

# 启动前后端开发服务器
pnpm dev
```

### 运行测试

```bash
python -m pytest tests/ -v       # 后端测试
cd web && npx vitest run          # 前端测试
```

### 项目结构

```
Agent/
├── src/agentos/        # Python 包核心
│   ├── cli/            # CLI 命令（Typer）
│   ├── core/           # 引擎核心（AgentRunner、SkillLoader 等）
│   ├── server/         # FastAPI 后端
│   └── builtin_skills/ # 内置 Skills
├── web/                # React 前端
├── tests/              # pytest 测试套件
├── examples/           # 示例 Agent 项目
└── docs/               # 开发文档
```

### 技术栈

| 层次 | 技术 |
|------|------|
| CLI | Typer + Rich |
| Web 后端 | FastAPI + SSE + uvicorn |
| LLM 调用 | LiteLLM（多厂商统一接口）|
| Web 前端 | React 18 + Vite + TypeScript + Tailwind CSS |
| 测试（后端）| pytest + pytest-anyio + httpx |
| 测试（前端）| Vitest + @testing-library/react |
| 打包 | hatchling（src-layout）|

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/开发指南.md](docs/开发指南.md) | 环境搭建、测试、构建、代码规范 |
| [docs/agent配置参考.md](docs/agent配置参考.md) | agent.toml 完整字段说明 |
| [docs/Skills开发规范.md](docs/Skills开发规范.md) | 编写 Skill 的完整规范 |
| [docs/core引擎模块说明.md](docs/core引擎模块说明.md) | Core 引擎各模块开发说明 |
| [docs/server模块开发说明.md](docs/server模块开发说明.md) | FastAPI 服务开发说明 |
| [docs/前端架构说明.md](docs/前端架构说明.md) | 前端架构、组件规范、扩展指南 |

---

## 示例项目

```bash
# 服装质检 Agent
cd examples/quality_inspection
agentos run

# 数据分析 Agent
cd examples/data_analysis
agentos run
```

---

## License

MIT — 详见 [LICENSE](LICENSE)
