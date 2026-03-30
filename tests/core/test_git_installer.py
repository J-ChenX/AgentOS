from pathlib import Path

from agentos.core.git_installer import GitInstaller, resolve_cache_path


class TestResolveCachePath:
    def test_github_url(self):
        path = resolve_cache_path("https://github.com/agentos-team/web-search.git", "v1.2.0")
        assert path == Path("github.com/agentos-team/web-search/v1.2.0")

    def test_gitlab_url(self):
        path = resolve_cache_path("https://gitlab.com/company/internal-tool.git", "v2.0.0")
        assert path == Path("gitlab.com/company/internal-tool/v2.0.0")

    def test_url_without_git_suffix(self):
        path = resolve_cache_path("https://github.com/user/repo", "v1.0.0")
        assert path == Path("github.com/user/repo/v1.0.0")

    def test_trailing_slash(self):
        path = resolve_cache_path("https://github.com/user/repo/", "v1.0.0")
        assert path == Path("github.com/user/repo/v1.0.0")


class TestGitInstaller:
    def test_get_absolute_cache_path(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        abs_path = installer.get_cache_path("https://github.com/user/repo.git", "v1.0.0")
        assert abs_path == tmp_path / "github.com" / "user" / "repo" / "v1.0.0"

    def test_is_cached_false_when_missing(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        assert installer.is_cached("https://github.com/user/repo.git", "v1.0.0") is False

    def test_is_cached_true_when_exists(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        cache = tmp_path / "github.com" / "user" / "repo" / "v1.0.0"
        cache.mkdir(parents=True)
        (cache / "skill.toml").write_text("[skill]\nname='test'\nversion='1.0.0'\n")
        assert installer.is_cached("https://github.com/user/repo.git", "v1.0.0") is True

    def test_read_manifest_returns_dict(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        cache = tmp_path / "github.com" / "user" / "repo" / "v1.0.0"
        cache.mkdir(parents=True)
        (cache / "skill.toml").write_text(
            'manifest_version = 1\n[skill]\nname = "test"\nversion = "1.0.0"\n'
            'description = "A test"\n[permissions]\nnetwork = true\n'
        )
        manifest = installer.read_manifest(cache)
        assert manifest["skill"]["name"] == "test"
        assert manifest["permissions"]["network"] is True

    def test_read_manifest_missing_raises(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        import pytest

        with pytest.raises(FileNotFoundError, match="skill.toml"):
            installer.read_manifest(tmp_path / "nonexistent")

    def test_extract_permissions_list(self, tmp_path):
        installer = GitInstaller(global_skills_dir=tmp_path)
        manifest = {
            "permissions": {
                "network": True,
                "file_read": False,
                "shell": True,
                "env_vars": ["API_KEY", "SECRET"],
            }
        }
        perms = installer.extract_permissions(manifest)
        assert "network" in perms
        assert "shell" in perms
        assert "env_vars:API_KEY" in perms
        assert "env_vars:SECRET" in perms
        assert "file_read" not in perms
