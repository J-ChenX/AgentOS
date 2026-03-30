from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from urllib.parse import urlparse


def resolve_cache_path(git_url: str, tag: str) -> Path:
    """从 Git URL + tag 解析相对缓存路径。

    示例：
      https://github.com/agentos-team/web-search.git, v1.2.0
      → github.com/agentos-team/web-search/v1.2.0
    """
    parsed = urlparse(git_url)
    host = parsed.hostname or ""
    path = parsed.path.strip("/").removesuffix(".git")
    return Path(host) / path / tag


class GitInstaller:
    """Git-based Skill 安装器。"""

    def __init__(self, global_skills_dir: Path | None = None):
        self.global_skills_dir = global_skills_dir or (Path.home() / ".agentos" / "skills")

    def get_cache_path(self, git_url: str, tag: str) -> Path:
        """返回全局缓存的绝对路径。"""
        return self.global_skills_dir / resolve_cache_path(git_url, tag)

    def is_cached(self, git_url: str, tag: str) -> bool:
        """检查指定版本是否已缓存。"""
        cache = self.get_cache_path(git_url, tag)
        return cache.exists() and (cache / "skill.toml").exists()

    def clone(self, git_url: str, tag: str) -> tuple[Path, str]:
        """克隆指定 tag 到全局缓存。返回 (缓存路径, commit hash)。

        Raises:
            RuntimeError: 如果 git clone 失败
            FileNotFoundError: 如果克隆后没有 skill.toml
        """
        cache = self.get_cache_path(git_url, tag)
        cache.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", tag, git_url, str(cache)],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git clone 失败：{e.stderr.strip()}") from e
        except FileNotFoundError:
            raise RuntimeError("未找到 git 命令。请确保已安装 Git CLI。") from None

        # 读取 commit hash
        commit = self._get_commit_hash(cache)

        # 验证 skill.toml 存在
        if not (cache / "skill.toml").exists():
            raise FileNotFoundError(f"仓库缺少 skill.toml manifest 文件：{git_url}@{tag}")

        return cache, commit

    def get_cached_commit(self, git_url: str, tag: str) -> str | None:
        """获取已缓存版本的 commit hash。"""
        cache = self.get_cache_path(git_url, tag)
        if not cache.exists():
            return None
        return self._get_commit_hash(cache)

    def _get_commit_hash(self, repo_dir: Path) -> str:
        """从 .git 目录读取 HEAD commit hash。"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def read_manifest(self, skill_dir: Path) -> dict:
        """读取 skill.toml manifest 文件。"""
        manifest_path = skill_dir / "skill.toml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"skill.toml 不存在：{manifest_path}")
        with open(manifest_path, "rb") as f:
            return tomllib.load(f)

    def extract_permissions(self, manifest: dict) -> list[str]:
        """从 manifest 提取权限列表。

        返回格式：["network", "shell", "env_vars:API_KEY", ...]
        """
        perms_section = manifest.get("permissions", {})
        result = []
        for key, value in perms_section.items():
            if key == "env_vars" and isinstance(value, list):
                for var in value:
                    result.append(f"env_vars:{var}")
            elif value is True:
                result.append(key)
        return result
