import os
import sys
from pathlib import Path

import typer
import uvicorn
from dotenv import find_dotenv, load_dotenv
from rich import print as rprint

from agentos.core.project_config import LLMConfig, ProjectConfig


def validate_api_key(llm_config: LLMConfig) -> None:
    """MVP pre-check: require API key when no local base_url is configured."""
    if not llm_config.base_url and not os.getenv(llm_config.api_key_env):
        raise ValueError(
            f"未配置 API Key。请在 agent/.env 中设置 {llm_config.api_key_env}，"
            "或在 agent/agent.toml [llm] 中配置 base_url（指向 OpenAI compat 端点）"
        )


def run_command(
    dev: bool = typer.Option(False, "--dev", help="开发模式（uvicorn --reload）"),
    port: int = typer.Option(8000, "--port", help="服务器端口"),
):
    """启动 Web UI 服务器"""
    project_dir = Path.cwd()
    agent_dir = project_dir / "agent"
    agent_toml = agent_dir / "agent.toml"

    if not agent_toml.exists():
        rprint("[red]错误：未找到 agent/agent.toml。运行 `agentos init <name>` 创建项目[/red]")
        raise typer.Exit(code=1)

    # 1. Search upward from project_dir for a root-level .env (e.g. monorepo root)
    root_env = find_dotenv(usecwd=True)
    if root_env:
        load_dotenv(root_env)

    # 2. Load agent-specific .env last so it overrides the root one
    env_file = agent_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    project_str = str(project_dir)
    if project_str not in sys.path:
        sys.path.insert(0, project_str)

    try:
        config = ProjectConfig.from_toml(agent_toml)
        validate_api_key(config.llm)
    except Exception as e:
        rprint(f"[red]配置错误: {e}[/red]")
        raise typer.Exit(code=1) from None

    rprint(f"[green]✓ 项目 '{config.name}' 已加载[/green]")

    if not dev:
        from agentos.server.app import WEB_ASSETS_DIR

        if not WEB_ASSETS_DIR.exists() or not any(WEB_ASSETS_DIR.iterdir()):
            rprint(
                "[yellow]提示：Web UI 资源未构建。使用 --dev 模式或运行 make build-web[/yellow]"
            )

    rprint(f"[blue]启动服务器 http://localhost:{port}[/blue]")

    uvicorn.run(
        "agentos.server.app:app",
        host="0.0.0.0",  # nosec B104 — intentional: local dev server binds all interfaces by design
        port=port,
        reload=dev,
    )
