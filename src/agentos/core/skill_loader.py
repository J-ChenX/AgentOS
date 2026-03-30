from __future__ import annotations

import importlib.util
import inspect
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentos.core.git_installer import resolve_cache_path
from agentos.core.tool import ToolSpec

if TYPE_CHECKING:
    from agentos.core.project_config import ProjectConfig


@dataclass
class SkillInfo:
    """Skill 元信息（用于 CLI 展示）"""

    name: str
    description: str
    source: str
    file_path: str
    version: str = ""
    enabled: bool = False


@dataclass
class LoadedSkill:
    """已加载的 Skill（用于运行时注入 Agent）"""

    name: str
    description: str
    source: str
    tool_functions: list[ToolSpec]
    version: str = ""
    permissions: dict | None = None
    overrides: dict | None = None


def _extract_tool_description(path: Path) -> str:
    """从 .py 文件中提取第一个 @tool 函数的 docstring"""
    try:
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            line = line.strip()
            if line.startswith('"""') and line.endswith('"""') and len(line) > 6:
                return line[3:-3]
            if line.startswith("'''") and line.endswith("'''") and len(line) > 6:
                return line[3:-3]
    except Exception:
        pass
    return ""


def _find_skill_entry(path: Path) -> Path | None:
    """找到 Skill 入口：.py 文件直接返回，目录优先找 skill.py，回退到 __init__.py。"""
    if path.is_file() and path.suffix == ".py":
        return path
    if path.is_dir():
        skill_py = path / "skill.py"
        if skill_py.exists():
            return skill_py
        init = path / "__init__.py"
        if init.exists() and init.stat().st_size > 0:
            return init
    return None


def _load_module_tools(entry_path: Path, module_name: str) -> list[Any]:
    """动态加载模块并提取 @tool 装饰的函数"""
    spec = importlib.util.spec_from_file_location(module_name, entry_path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return []
    tools = []
    for name, obj in inspect.getmembers(module):
        if isinstance(obj, ToolSpec) and not name.startswith("_"):
            tools.append(obj)
    return tools


class SkillLoader:
    """Skills 发现与加载器。区分全量发现（CLI）和按需加载（运行时）。"""

    def __init__(self, project_dir: Path, config: ProjectConfig):
        self.project_dir = project_dir
        self.project_skills_dir = project_dir / "agent" / "skills"
        self.global_skills_dir = Path.home() / ".agentos" / "skills"
        self.builtin_skills_dir = Path(__file__).parent.parent / "builtin_skills"
        self.config = config

    def get_available_skills(self) -> list[SkillInfo]:
        """全量扫描三层目录（CLI 展示用）。"""
        skills: dict[str, SkillInfo] = {}
        for s in self._scan_dir(self.builtin_skills_dir, source="builtin"):
            skills[s.name] = s
        # Spec A 遗留：扫描扁平全局目录（向后兼容）
        for s in self._scan_dir(self.global_skills_dir, source="global"):
            skills[s.name] = s
        # Spec B+C：扫描版本化缓存目录树
        for s in self._scan_versioned_cache():
            skills[s.name] = s
        for s in self._scan_dir(self.project_skills_dir, source="local"):
            skills[s.name] = s
        for name in self.config.skills:
            if name in skills:
                skills[name].enabled = True
        return list(skills.values())

    def load_project_skills(self) -> list[LoadedSkill]:
        """严格按 agent.toml [skills] 声明按需加载。"""
        active_skills: list[LoadedSkill] = []
        for skill_alias, skill_config in self.config.skills.items():
            # Spec A: 本地路径
            if "path" in skill_config:
                skill_path = (self.project_dir / skill_config["path"]).resolve()
                source = "local"
            # Spec B+C: Git 引用
            elif "git" in skill_config:
                rel = resolve_cache_path(skill_config["git"], skill_config["tag"])
                skill_path = self.global_skills_dir / rel
                source = "git"
                if not skill_path.exists():
                    raise RuntimeError(
                        f"Skill '{skill_alias}' 未安装。运行 `agentos skill install`"
                    )
            # Spec A: 内置
            elif skill_config.get("source") == "builtin":
                skill_path = self.builtin_skills_dir / skill_alias
                source = "builtin"
            # Spec A 遗留：扁平全局目录（已废弃，保持向后兼容）
            elif skill_config.get("source") == "global":
                skill_path = self.global_skills_dir / skill_alias
                source = "global"
            else:
                raise ValueError(f"Skill '{skill_alias}' 在 agent.toml 中配置无法解析")

            entry = _find_skill_entry(skill_path)
            if entry is None:
                active_skills.append(
                    LoadedSkill(
                        name=skill_alias,
                        description="",
                        source=source,
                        tool_functions=[],
                    )
                )
                continue

            tools = _load_module_tools(entry, f"skill_{skill_alias}")
            desc = _extract_tool_description(entry)

            # 读取版本和权限（如有 skill.toml）
            version = ""
            permissions = None
            manifest_path = skill_path / "skill.toml" if skill_path.is_dir() else None
            if manifest_path and manifest_path.exists():
                with open(manifest_path, "rb") as f:
                    manifest = tomllib.load(f)
                version = manifest.get("skill", {}).get("version", "")
                permissions = manifest.get("permissions")

            loaded = LoadedSkill(
                name=skill_alias,  # alias overrides original name
                description=desc,
                source=source,
                tool_functions=tools,
                version=version,
                permissions=permissions,
            )

            # Soft Eject overrides
            if "override" in skill_config:
                loaded.overrides = skill_config["override"]
                # 应用 prompt 覆写到 tool description
                if "prompt" in skill_config["override"] and tools:
                    for t in tools:
                        if hasattr(t, "description"):
                            t.description = skill_config["override"]["prompt"]

            active_skills.append(loaded)
        return active_skills

    def _scan_dir(self, directory: Path, source: str) -> list[SkillInfo]:
        """扫描一级目录，发现 .py 文件和含 __init__.py/skill.py 的子目录。"""
        if not directory.exists():
            return []
        results: list[SkillInfo] = []
        for item in sorted(directory.iterdir()):
            if item.name.startswith("_"):
                continue
            if item.is_file() and item.suffix == ".py":
                name = item.stem
                desc = _extract_tool_description(item)
                results.append(
                    SkillInfo(
                        name=name,
                        description=desc,
                        source=source,
                        file_path=str(item),
                    )
                )
            elif item.is_dir():
                entry = _find_skill_entry(item)
                if entry is not None:
                    desc = _extract_tool_description(entry)
                    version = self._read_version(item)
                    results.append(
                        SkillInfo(
                            name=item.name,
                            description=desc,
                            source=source,
                            file_path=str(item),
                            version=version,
                        )
                    )
        return results

    def _scan_versioned_cache(self) -> list[SkillInfo]:
        """遍历 ~/.agentos/skills/ 版本化缓存目录树。

        对每个 host/user/repo/ 找到最新版本的 skill.toml 并提取信息。
        """
        if not self.global_skills_dir.exists():
            return []
        results = []
        for host_dir in sorted(self.global_skills_dir.iterdir()):
            # 跳过非域名目录（Spec A 遗留的扁平 Skill 目录没有 '.'）
            if not host_dir.is_dir() or host_dir.name.startswith("_") or "." not in host_dir.name:
                continue
            for user_dir in sorted(host_dir.iterdir()):
                if not user_dir.is_dir():
                    continue
                for repo_dir in sorted(user_dir.iterdir()):
                    if not repo_dir.is_dir():
                        continue
                    # 找所有版本目录，取最新
                    versions = sorted(
                        [v for v in repo_dir.iterdir() if v.is_dir()],
                        key=lambda v: self._version_sort_key(v.name),
                        reverse=True,
                    )
                    if versions:
                        latest = versions[0]
                        manifest_path = latest / "skill.toml"
                        if manifest_path.exists():
                            info = self._parse_manifest(manifest_path, source="global")
                            results.append(info)
        return results

    def _parse_manifest(self, manifest_path: Path, source: str) -> SkillInfo:
        """从 skill.toml 解析 SkillInfo。"""
        with open(manifest_path, "rb") as f:
            data = tomllib.load(f)
        skill = data.get("skill", {})
        return SkillInfo(
            name=skill.get("name", manifest_path.parent.parent.name),
            description=skill.get("description", ""),
            source=source,
            file_path=str(manifest_path.parent),
            version=skill.get("version", ""),
        )

    def _read_version(self, skill_dir: Path) -> str:
        """尝试从 skill.toml 读取版本号。"""
        manifest = skill_dir / "skill.toml"
        if manifest.exists():
            try:
                with open(manifest, "rb") as f:
                    data = tomllib.load(f)
                return data.get("skill", {}).get("version", "")
            except Exception:
                pass
        return ""

    @staticmethod
    def _version_sort_key(version_str: str):
        """使用 packaging.version.Version 解析 SemVer 排序。"""
        from packaging.version import InvalidVersion, Version

        try:
            return Version(version_str.lstrip("v"))
        except InvalidVersion:
            return Version("0")
