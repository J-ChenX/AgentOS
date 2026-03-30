from pathlib import Path

import typer

from agentos.cli.init_cmd import init_command
from agentos.cli.run_cmd import run_command
from agentos.cli.skill_cmd import skill_app

app = typer.Typer(
    name="agentos",
    help="AgentOS — 在任意目录拉起 AI 智能体",
)

app.command("init")(init_command)
app.command("run")(run_command)
app.add_typer(skill_app, name="skill")


@app.command("version")
def version_command():
    """显示版本信息"""
    from agentos import __version__

    typer.echo(f"AgentOS v{__version__}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    if (Path("agent") / "agent.toml").exists():
        run_command()
    else:
        typer.echo("当前目录未找到 agent/agent.toml")
        if typer.confirm("要在此目录初始化 Agent 项目吗？"):
            name = typer.prompt("项目名称")
            init_command(name)
