# AgentOS — 可复用 AI Agent 框架

在任意目录运行 `agentos` 拉起 AI 智能体，通过 Web UI 对话式交互。

## 项目结构

```
Agent/                              ← monorepo 根
├── pyproject.toml                  ← Python 包配置（hatchling，pip install -e ".[dev]"）
├── Makefile                        ← 构建编排（make build-web / make build）
├── .env                            ← 环境变量（不提交 VCS）
├── agent-lock.toml                 ← Skills 版本锁定文件（Git Skills 的 commit + 审批权限）
│
├── src/agentos/                    ← 框架核心（pip 安装的包）
│   ├── cli/                        ← CLI 命令（Typer）
│   │   ├── app.py                  ← 主入口 + 命令注册
│   │   ├── init_cmd.py             ← agentos init <name>
│   │   ├── run_cmd.py              ← agentos run [--dev] [--port]
│   │   └── skill_cmd.py            ← agentos skill list/add/eject/install/update/remove/info
│   ├── core/                       ← Core 引擎接口
│   │   ├── project_config.py       ← agent.toml 解析（tomllib）+ scope 字段
│   │   ├── skill_loader.py         ← Skills 三层解析 + 版本化路径 + 别名 + overrides
│   │   ├── llm.py                  ← LLM 工厂
│   │   ├── runner.py               ← AgentRunner stub（Spec 1 实现）
│   │   ├── file_scope.py           ← FileScope 文件访问控制
│   │   ├── lock_manager.py         ← agent-lock.toml 读写
│   │   ├── git_installer.py        ← Git clone + commit 校验
│   │   └── permission_checker.py   ← 权限审批 + 运行时校验
│   ├── server/                     ← FastAPI 后端（Web UI API）
│   │   ├── app.py                  ← create_app(dev_mode) + StaticFiles 挂载
│   │   ├── models.py               ← Pydantic 模型
│   │   ├── sse.py                  ← SSE 流式响应
│   │   ├── stub_engine.py          ← Stub 引擎
│   │   └── routes/                 ← API 路由
│   ├── builtin_skills/             ← 框架内置 Skills（随 pip 分发）
│   │   ├── _common.py              ← 共享运行时上下文接口（FileScope 注入）
│   │   ├── file_reader/            ← 读取项目文件（含 skill.toml manifest）
│   │   ├── web_search/             ← 网页搜索 stub（含 skill.toml manifest）
│   │   └── system_shell/           ← 执行 shell stub（含 skill.toml manifest + 危险命令黑名单）
│   └── _web_assets/                ← 前端构建产物（make build-web 生成）
│
├── web/                            ← 前端源码（React + Vite + TypeScript）
│   ├── src/                        ← 组件、类型、适配器、hooks
│   └── tests/                      ← Vitest 测试
│
├── examples/                       ← 示例 Agent 项目
│   ├── quality_inspection/         ← 服装质检 Agent
│   └── data_analysis/              ← ABT 数据分析 Agent
│
├── tests/                          ← 框架测试（pytest）
│   ├── cli/                        ← CLI 命令测试
│   ├── core/                       ← Core 模块测试
│   └── server/                     ← API 端点测试
│
└── docs/                           ← 开发文档
    ├── specs/                      ← 设计文档 + 实现计划
    └── *.md                        ← 详细开发指南（CLI、agent.toml、Skills 开发等）
```

## CLI 命令

```bash
agentos                           # 智能入口（有 agent.toml 则启动，否则引导初始化）
agentos init <name>               # 创建标准 Agent 项目
agentos run [--dev] [--port PORT] # 启动 Web UI 服务器
agentos skill list                # 列出可用 Skills（含版本列）
agentos skill add <name>          # 在 agent.toml 中声明引用
agentos skill add <name> --git <url> --tag <tag>  # 添加 Git 源 Skill 并自动安装
agentos skill install [name]      # 按 agent.toml 安装所有 Git Skills（含权限审批）
agentos skill update <name>       # 更新 Skill 到 agent.toml 声明的新 tag
agentos skill remove <name>       # 从 agent.toml + agent-lock.toml 移除 Skill
agentos skill info <name>         # 显示 Skill 详情（来源、版本、权限）
agentos skill eject <name>        # 复制到项目本地（支持 Git/内置源，脱离升级）
agentos version                   # 版本信息
```

## 开发设置

```bash
pip install -e ".[dev]"           # 安装框架 + 开发依赖
pnpm install                      # 安装前端依赖（monorepo 根目录）
pnpm dev                          # 同时启动前端 HMR + 后端（推荐）
# 浏览器: http://localhost:6493
```

## 技术栈

- **CLI**: Typer + Rich
- **Web 后端**: FastAPI + SSE + uvicorn
- **Web 前端**: React 18 + Vite + TypeScript + Tailwind + react-mosaic
- **Agent 框架**: LangGraph + LangChain
- **配置**: tomlkit（保真读写 agent.toml）
- **打包**: hatchling（src-layout）

## 开发约定

- 框架代码在 `src/agentos/`，import 路径以 `agentos.` 开头
- 示例项目在 `examples/`，使用本地绝对 import（非相对 import）
- Skills 使用 `@tool` 装饰器，放在 `skills/` 目录
- agent.toml 是 Skills 的唯一 Truth Source — 运行时只加载声明过的 Skills
- agent.toml 的 `[skills]` key 作为 LLM tool name（别名覆盖），支持 `override` 字段（Soft Eject）
- Git 源 Skills 通过 `{ git = "...", tag = "..." }` 声明，安装到 `~/.agentos/skills/` 版本化缓存
- agent-lock.toml 记录 Git Skills 的 commit hash + 已审批权限，需提交到版本控制
- 每个内置 Skill 必须包含 `skill.toml` manifest 文件（声明版本、权限）
- FileScope（`core/file_scope.py`）控制 Skill 文件访问范围，由 AgentRunner 注入
- LLM 实例通过 `agentos.core.llm.create_llm()` 工厂创建
- `.env` 文件包含敏感凭证，不可提交到版本控制
- 测试：`python -m pytest tests/ -v`（后端），`cd web && npx vitest run`（前端）
