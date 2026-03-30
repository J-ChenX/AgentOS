from pathlib import Path

import typer
from rich import print as rprint

AGENT_TOML_TEMPLATE = """\
[project]
name = "{name}"
version = "0.1.0"

[llm]
model = "{model}"
base_url = "{base_url}"

[agent]
type = "react"
max_iterations = 20
system_prompt_path = "agent.md"
memory_path = "memory.md"

[scope]
allow = ["./"]
deny = [".env", "*.key", "memory_store/"]

[skills]
# 文件操作
file_reader     = {{ source = "builtin" }}
file_writer     = {{ source = "builtin" }}
file_editor     = {{ source = "builtin" }}
file_search     = {{ source = "builtin" }}
content_search  = {{ source = "builtin" }}

# 系统交互
system_shell    = {{ source = "builtin", safe_commands = [
    "ls", "pwd", "cat", "head", "tail", "echo", "wc",
    "find", "grep", "which", "env", "date", "whoami",
    "python --version", "node --version",
    "git status", "git log", "git diff", "pip list"
], confirm_mode = "unsafe" }}

# 网络
web_search      = {{ source = "builtin" }}

# 用户交互与任务管理
ask_user        = {{ source = "builtin" }}
todo_manager    = {{ source = "builtin" }}

# 记忆系统
memory_writer   = {{ source = "builtin" }}
"""

AGENT_MD_TEMPLATE = """\
# {name}

你是一个 AI 智能体，请遵循以下工作规范。

## 工具使用规则

- 使用 read_file 阅读文件时，注意返回的行号是绝对行号
- 使用 edit_file 编辑文件时：
  - 先用 read_file 获取带行号的内容
  - 调用 edit_file 时务必传入 expected_snippet 参数（目标首行的关键片段），防止并发修改导致行号错位
  - 每次 edit_file 后文件行号可能变化，必须重新 read_file 获取最新行号
  - 禁止基于旧行号连续操作同一文件
- 使用 write_file 覆写文件前，先用 read_file 确认目标文件内容
- 使用 run_shell 执行命令时，非只读命令可能需要用户确认
- 复杂任务请使用 update_todos 跟踪进度
- 需要用户确认关键决策时使用 ask_user

## 记忆系统管理规范

你拥有双层记忆系统，请严格按规则管理知识：

### L1 核心记忆 (agent/memory.md)

全局主控记忆，采用二级标题（##）分区。

- **触发条件**：学到全局性规范、用户偏好、核心架构决策时
- **操作方式**：使用 `replace_section` 工具，精准替换 `memory.md` 中的对应分区。
  不要写入长篇代码或错误日志

### L2 扩展记忆 (agent/memory_store/)

长期主题档案，按需创建。

- **触发条件**：排查复杂 Bug 或梳理超过 50 行的文档时
- **操作方式**：
  1. 使用 `append_to_file` 工具，在 `memory_store/` 下新建或追加专题 `.md` 文件
  2. 回到 `memory.md` 的「## 知识库索引」分区，使用 `replace_section` 添加一行索引说明
  3. **定期检查索引**：如果发现某个旧有的 `.md` 文件已彻底过时并被新文件取代，
     主动删除旧文件并更新 `memory.md` 的索引
"""

MEMORY_MD_TEMPLATE = """\
# 核心记忆

## 用户偏好

## 项目规范

## 知识库索引
"""

HELLO_SKILL = '''\
"""Hello Skill — 示例技能

演示标准 Skill 的编写规范。每个 Skill 函数必须包含：
1. 清晰的 docstring（描述功能、参数、返回值）
2. @tool 装饰器注册为 Agent 可调用工具

工作流程: 用户请求打招呼 → Agent 调用此技能 → 返回问候语
"""

from langchain_core.tools import tool


@tool
def hello(name: str) -> str:
    """向指定用户打招呼。

    Args:
        name: 用户的名字

    Returns:
        包含用户名字的问候语
    """
    return f"你好, {name}! 我是你的 AI 助手。"
'''

ENV_EXAMPLE = """\
# 复制此文件为 .env 并填入你的 API Key
# cp .env.example .env

# LLM API 密钥
LLM_API_KEY=your-api-key-here

# （可选）其他服务密钥
# SEARCH_API_KEY=
"""


def _load_env_vars(cwd: Path) -> dict[str, str]:
    """Search cwd and parent directories for a .env file, return its key=value pairs."""
    for directory in [cwd, *cwd.parents]:
        env_file = directory / ".env"
        if env_file.exists():
            result: dict[str, str] = {}
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    result[k.strip()] = v.strip()
            return result
    return {}


def _ensure_gitignore(project_dir: Path) -> None:
    """确保 .gitignore 包含 agent/.env 规则。安全硬性要求，不可跳过。"""
    gitignore = project_dir / ".gitignore"
    entry = "agent/.env"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry in content:
            return
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n# AgentOS — 防止 API Key 泄露\n{entry}\n"
        gitignore.write_text(content, encoding="utf-8")
    else:
        gitignore.write_text(f"# AgentOS — 防止 API Key 泄露\n{entry}\n", encoding="utf-8")


def init_command(name: str = typer.Argument(..., help="项目名称")):
    """创建标准 Agent 项目"""
    project_dir = Path.cwd() / name
    agent_dir = project_dir / "agent"

    if (agent_dir / "agent.toml").exists():
        rprint(f"[red]错误：{project_dir} 已是 Agent 项目[/red]")
        raise typer.Exit(code=1)

    env_vars = _load_env_vars(Path.cwd())
    base_url = env_vars.get("GEMINI_BASE_URL", "")
    model = env_vars.get("GEMINI_MODEL", "gemini-2.0-flash")

    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "skills").mkdir(exist_ok=True)

    (agent_dir / "agent.toml").write_text(
        AGENT_TOML_TEMPLATE.format(name=name, base_url=base_url, model=model),
        encoding="utf-8",
    )
    (agent_dir / "agent.md").write_text(
        AGENT_MD_TEMPLATE.format(name=name), encoding="utf-8"
    )
    (agent_dir / "memory.md").write_text(MEMORY_MD_TEMPLATE, encoding="utf-8")
    (agent_dir / ".env.example").write_text(ENV_EXAMPLE, encoding="utf-8")
    (agent_dir / "skills" / "hello.py").write_text(HELLO_SKILL, encoding="utf-8")

    _ensure_gitignore(project_dir)

    rprint(f"[green]✓ 项目 '{name}' 创建成功[/green]")
    if base_url:
        rprint(f"[dim]  LLM: {model} → {base_url}[/dim]")
    else:
        rprint("[yellow]  提示：请在 agent/agent.toml [llm] 中填写 base_url[/yellow]")
    rprint(f"  cd {name}")
    rprint("  agentos run --dev --port 8000")
