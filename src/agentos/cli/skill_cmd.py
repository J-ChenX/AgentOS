import shutil
from pathlib import Path

import tomlkit
import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from agentos.core.git_installer import GitInstaller
from agentos.core.lock_manager import LockEntry, LockManager
from agentos.core.permission_checker import format_permissions_display
from agentos.core.project_config import ProjectConfig
from agentos.core.skill_loader import SkillLoader

skill_app = typer.Typer(help="Skills 管理")
console = Console()


def _load_context() -> tuple[Path, ProjectConfig, SkillLoader]:
    project_dir = Path.cwd()
    toml_path = project_dir / "agent.toml"
    if not toml_path.exists():
        rprint("[red]错误：未找到 agent.toml[/red]")
        raise typer.Exit(code=1)
    config = ProjectConfig.from_toml(toml_path)
    loader = SkillLoader(project_dir, config)
    return project_dir, config, loader


def _install_git_skill(
    skill_name: str,
    skill_config: dict,
    lock_mgr: LockManager,
    installer: GitInstaller,
    yes: bool = False,
) -> bool:
    """安装单个 Git Skill 的核心逻辑（供 install 和 add --git 共用）。返回是否成功。"""
    git_url = skill_config["git"]
    tag = skill_config["tag"]
    rprint(f"\n[bold]正在处理 {skill_name}...[/bold]")

    existing_lock = lock_mgr.get_lock(skill_name)

    # 检查缓存
    if installer.is_cached(git_url, tag):
        cached_commit = installer.get_cached_commit(git_url, tag)
        if existing_lock and existing_lock.commit == cached_commit:
            rprint("  [dim]已缓存且校验通过，跳过[/dim]")
            return True
        elif existing_lock and cached_commit and existing_lock.commit != cached_commit:
            rprint("  [red]⚠ 校验和不匹配！远程 Tag 可能已被篡改[/red]")
            raise typer.Exit(code=1)

    # Clone
    try:
        rprint(f"  正在克隆 {git_url}@{tag} ...")
        cache_path, commit = installer.clone(git_url, tag)
        rprint(f"  ✓ 克隆完成 (commit: {commit[:8]})")
    except (RuntimeError, FileNotFoundError) as e:
        rprint(f"  [red]错误：{e}[/red]")
        raise typer.Exit(code=1) from None

    # 安全校验
    if existing_lock and existing_lock.commit and existing_lock.commit != commit:
        rprint("  [red]⚠ 校验和不匹配！远程 Tag 可能已被篡改[/red]")
        raise typer.Exit(code=1)

    # 读取 manifest + 权限
    manifest = installer.read_manifest(cache_path)
    permissions = installer.extract_permissions(manifest)

    # 审批
    new_perms = lock_mgr.get_new_permissions(skill_name, permissions)
    if new_perms:
        rprint(f"\n  ⚠ Skill '{skill_name}' 请求以下权限：")
        for line in format_permissions_display(new_perms):
            rprint(f"  {line}")
        if yes:
            rprint("  [red]CI 模式下需要人工审批新增权限[/red]")
            raise typer.Exit(code=1)
        if not typer.confirm("\n  是否信任此 Skill 并授予以上权限？"):
            rprint(f"  [yellow]已跳过 {skill_name}[/yellow]")
            return False

    # 合并权限
    all_approved = list(
        set((existing_lock.approved_permissions if existing_lock else []) + permissions)
    )

    from agentos.core.git_installer import resolve_cache_path

    lock_mgr.set_lock(
        skill_name,
        LockEntry(
            git=git_url,
            tag=tag,
            commit=commit,
            resolved_path=str(resolve_cache_path(git_url, tag)),
            approved_permissions=sorted(all_approved),
        ),
    )
    return True


@skill_app.command("list")
def skill_list():
    """列出可用 Skills（本地 + 全局 + 内置）"""
    project_dir, config, loader = _load_context()
    skills = loader.get_available_skills()

    table = Table(title="可用 Skills")
    table.add_column("来源", style="dim")
    table.add_column("名称", style="bold")
    table.add_column("版本")
    table.add_column("描述")
    table.add_column("已启用", justify="center")

    for s in skills:
        enabled = "✓" if s.enabled else ""
        table.add_row(s.source, s.name, s.version or "-", s.description, enabled)

    console.print(table)


@skill_app.command("add")
def skill_add(
    name: str = typer.Argument(..., help="Skill 名称（在 agent.toml 中的别名）"),
    git: str = typer.Option(None, "--git", help="Git 仓库 URL"),
    tag: str = typer.Option(None, "--tag", help="Git tag（版本）"),
):
    """在 agent.toml 中声明 Skill 引用（不复制文件）"""
    project_dir, config, loader = _load_context()
    toml_path = project_dir / "agent.toml"
    doc = tomlkit.parse(toml_path.read_text(encoding="utf-8"))

    if "skills" not in doc:
        doc.add("skills", tomlkit.table())

    # Git 模式：声明 + 自动安装
    if git:
        if not tag:
            rprint("[red]错误：使用 --git 时必须指定 --tag[/red]")
            raise typer.Exit(code=1)

        inline = tomlkit.inline_table()
        inline.append("git", git)
        inline.append("tag", tag)
        doc["skills"][name] = inline
        toml_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        rprint(f"[green]✓ 已将 {name} 添加到 agent.toml[/green]")

        # 自动触发 install（重新加载 config 以读取刚写入的 git 条目）
        config = ProjectConfig.from_toml(toml_path)
        lock_mgr = LockManager(project_dir / "agent-lock.toml")
        installer = GitInstaller()
        _install_git_skill(name, config.skills[name], lock_mgr, installer)
        lock_mgr.save()
        return

    # 原有逻辑：从 available skills 中添加引用
    available = {s.name: s for s in loader.get_available_skills()}
    if name not in available:
        rprint(
            f"[red]错误：Skill '{name}' 未找到。运行 `agentos skill list` 查看可用 Skills[/red]"
        )
        raise typer.Exit(code=1)

    skill_info = available[name]
    source = skill_info.source
    if source == "local":
        doc["skills"][name] = {"path": f"./skills/{name}"}
    else:
        doc["skills"][name] = {"source": source}

    toml_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    rprint(f"[green]✓ 已将 {name} 添加到 agent.toml[/green]")


@skill_app.command("install")
def skill_install(
    name: str | None = typer.Argument(None, help="安装指定 Skill（不指定则安装全部）"),
    yes: bool = typer.Option(False, "--yes", "-y", help="CI 模式：跳过已审批权限的确认"),
):
    """按 agent.toml + lock 文件安装所有 Git Skills"""
    project_dir, config, loader = _load_context()
    lock_path = project_dir / "agent-lock.toml"
    lock_mgr = LockManager(lock_path)
    installer = GitInstaller()

    git_skills = {k: v for k, v in config.skills.items() if "git" in v}

    if name:
        if name not in git_skills:
            rprint(f"[red]错误：Skill '{name}' 不是 Git 引用类型[/red]")
            raise typer.Exit(code=1)
        git_skills = {name: git_skills[name]}

    if not git_skills:
        rprint("[green]无需安装 Git Skills[/green]")
        return

    for skill_name, skill_config in git_skills.items():
        _install_git_skill(skill_name, skill_config, lock_mgr, installer, yes=yes)

    lock_mgr.save()
    rprint("\n[green]✓ 安装完成，agent-lock.toml 已更新[/green]")


@skill_app.command("update")
def skill_update(name: str = typer.Argument(..., help="Skill 名称")):
    """更新 Skill 到 agent.toml 声明的新 tag"""
    project_dir, config, loader = _load_context()

    skill_config = config.skills.get(name)
    if not skill_config or "git" not in skill_config:
        rprint(f"[red]错误：Skill '{name}' 不是 Git 引用类型[/red]")
        raise typer.Exit(code=1)

    lock_path = project_dir / "agent-lock.toml"
    lock_mgr = LockManager(lock_path)
    existing = lock_mgr.get_lock(name)

    new_tag = skill_config["tag"]
    if existing and existing.tag == new_tag:
        rprint(f"[dim]{name} 已是最新版本 ({new_tag})，无需更新[/dim]")
        return

    if existing:
        rprint(f"更新 {name}: {existing.tag} → {new_tag}")
    else:
        rprint(f"安装 {name}: {new_tag}")

    installer = GitInstaller()
    _install_git_skill(name, skill_config, lock_mgr, installer)
    lock_mgr.save()
    rprint(f"\n[green]✓ 已更新到 {new_tag}[/green]")


@skill_app.command("remove")
def skill_remove(name: str = typer.Argument(..., help="Skill 名称")):
    """从 agent.toml 移除 Skill 声明"""
    project_dir, config, loader = _load_context()

    toml_path = project_dir / "agent.toml"
    doc = tomlkit.parse(toml_path.read_text(encoding="utf-8"))

    if "skills" not in doc or name not in doc["skills"]:
        rprint(f"[red]错误：Skill '{name}' 不在 agent.toml 中[/red]")
        raise typer.Exit(code=1)

    del doc["skills"][name]
    toml_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    rprint(f"[green]✓ 已从 agent.toml 中移除 {name}[/green]")

    # 移除 lock 记录
    lock_path = project_dir / "agent-lock.toml"
    if lock_path.exists():
        lock_mgr = LockManager(lock_path)
        if lock_mgr.get_lock(name):
            lock_mgr.remove_lock(name)
            lock_mgr.save()
            rprint("[green]✓ 已从 agent-lock.toml 中移除锁定记录[/green]")

    rprint("[dim]全局缓存保留，可手动清理 ~/.agentos/skills/[/dim]")


@skill_app.command("info")
def skill_info(name: str = typer.Argument(..., help="Skill 名称")):
    """显示 Skill 详情（来源、版本、权限）"""
    project_dir, config, loader = _load_context()

    # 在 agent.toml 中查找
    skill_config = config.skills.get(name)

    # 确定来源和路径
    skill_path = None
    source = "unknown"
    version = ""

    if skill_config:
        if "path" in skill_config:
            skill_path = (project_dir / skill_config["path"]).resolve()
            source = "local"
        elif "git" in skill_config:
            from agentos.core.git_installer import resolve_cache_path

            rel = resolve_cache_path(skill_config["git"], skill_config["tag"])
            skill_path = loader.global_skills_dir / rel
            source = f"git ({skill_config['git']})"
            version = skill_config.get("tag", "")
        elif skill_config.get("source") == "builtin":
            skill_path = loader.builtin_skills_dir / name
            source = "builtin"
    else:
        # 尝试在 available skills 中查找
        available = {s.name: s for s in loader.get_available_skills()}
        if name in available:
            skill_path = Path(available[name].file_path)
            source = available[name].source
            version = available[name].version
        else:
            rprint(f"[red]错误：Skill '{name}' 未找到[/red]")
            raise typer.Exit(code=1)

    rprint(f"\n[bold]Skill: {name}[/bold]")
    rprint(f"  来源: {source}")
    if version:
        rprint(f"  版本: {version}")

    # 读取 manifest（如有）
    if skill_path and skill_path.is_dir():
        manifest_path = skill_path / "skill.toml"
        if manifest_path.exists():
            import tomllib

            with open(manifest_path, "rb") as f:
                manifest = tomllib.load(f)
            skill_meta = manifest.get("skill", {})
            rprint(f"  描述: {skill_meta.get('description', '')}")
            rprint(f"  作者: {skill_meta.get('author', '')}")

            perms = manifest.get("permissions", {})
            rprint("\n  权限声明:")
            for key, value in perms.items():
                if key == "env_vars" and isinstance(value, list):
                    status = "✓" if value else "✗"
                    rprint(f"    {status} env_vars    — {', '.join(value) if value else '无'}")
                else:
                    status = "✓" if value else "✗"
                    label = {
                        "file_read": "文件读取",
                        "file_write": "文件写入",
                        "network": "网络访问",
                        "shell": "Shell 命令",
                    }.get(key, key)
                    rprint(f"    {status} {key:<12} — {label}")

    # Lock 状态
    lock_path = project_dir / "agent-lock.toml"
    if lock_path.exists():
        lock_mgr = LockManager(lock_path)
        lock_entry = lock_mgr.get_lock(name)
        if lock_entry:
            rprint("\n  审批状态: [green]已审批[/green] (agent-lock.toml)")
            rprint(f"  Commit: {lock_entry.commit[:12]}")


@skill_app.command("eject")
def skill_eject(name: str = typer.Argument(..., help="Skill 名称")):
    """将全局/内置/Git Skill 复制到项目 skills/（脱离升级）"""
    project_dir, config, loader = _load_context()

    local_dir = project_dir / "skills" / name
    if local_dir.exists():
        rprint(f"[red]错误：Skill '{name}' 已在本地 skills/ 中[/red]")
        raise typer.Exit(code=1)

    source_path = None
    skill_config = config.skills.get(name, {})

    # Git 源：从版本化缓存复制
    if "git" in skill_config:
        installer = GitInstaller()
        source_path = installer.get_cache_path(skill_config["git"], skill_config["tag"])
        if not source_path.exists():
            rprint(f"[red]错误：Skill '{name}' 未安装。运行 `agentos skill install`[/red]")
            raise typer.Exit(code=1)
    # 内置
    elif (loader.builtin_skills_dir / name).exists():
        source_path = loader.builtin_skills_dir / name
    # 全局（Spec A 遗留，但保持兼容）
    elif (loader.global_skills_dir / name).exists():
        source_path = loader.global_skills_dir / name

    if source_path is None:
        rprint(f"[red]错误：Skill '{name}' 未找到[/red]")
        raise typer.Exit(code=1)

    shutil.copytree(source_path, local_dir, ignore=shutil.ignore_patterns(".git"))
    rprint(f"[green]✓ 已将 {name} 复制到 skills/{name}/[/green]")

    # 更新 agent.toml：替换为本地路径
    toml_path = project_dir / "agent.toml"
    doc = tomlkit.parse(toml_path.read_text(encoding="utf-8"))
    if "skills" not in doc:
        doc.add("skills", tomlkit.table())
    doc["skills"][name] = {"path": f"./skills/{name}"}
    toml_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    # 移除 lock 记录（本地代码不需要锁定）
    lock_path = project_dir / "agent-lock.toml"
    if lock_path.exists():
        lock_mgr = LockManager(lock_path)
        if lock_mgr.get_lock(name):
            lock_mgr.remove_lock(name)
            lock_mgr.save()

    rprint("[yellow]注意：此 Skill 已脱离远端版本，不会自动接收更新[/yellow]")
