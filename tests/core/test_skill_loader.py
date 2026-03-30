from agentos.core.project_config import ProjectConfig
from agentos.core.skill_loader import SkillLoader


class TestSkillLoader:
    def _make_loader(self, tmp_path, skills_config=None):
        config = ProjectConfig(skills=skills_config or {})
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        return SkillLoader(project_dir, config)

    def test_project_skills_dir_points_to_agent_skills(self, tmp_path):
        loader = self._make_loader(tmp_path)
        assert loader.project_skills_dir == tmp_path / "project" / "agent" / "skills"

    def test_scan_dir_finds_py_files(self, tmp_path):
        loader = self._make_loader(tmp_path)
        skill_dir = tmp_path / "skills_src"
        skill_dir.mkdir()
        (skill_dir / "hello.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def hello(name: str) -> str:\n    """Say hello"""\n    return f"hi {name}"\n'
        )
        results = loader._scan_dir(skill_dir, source="test")
        assert len(results) == 1
        assert results[0].name == "hello"
        assert results[0].source == "test"

    def test_scan_dir_finds_package_dirs(self, tmp_path):
        loader = self._make_loader(tmp_path)
        skill_dir = tmp_path / "skills_src"
        skill_dir.mkdir()
        pkg = skill_dir / "my_tool"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "skill.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def my_tool() -> str:\n    """Do something"""\n    return "done"\n'
        )
        results = loader._scan_dir(skill_dir, source="test")
        assert len(results) == 1
        assert results[0].name == "my_tool"

    def test_scan_dir_ignores_non_skill_dirs(self, tmp_path):
        loader = self._make_loader(tmp_path)
        skill_dir = tmp_path / "skills_src"
        skill_dir.mkdir()
        pkg = skill_dir / "not_a_skill"
        pkg.mkdir()
        (pkg / "helper.py").write_text("x = 1")
        results = loader._scan_dir(skill_dir, source="test")
        assert len(results) == 0

    def test_scan_dir_empty_returns_empty(self, tmp_path):
        loader = self._make_loader(tmp_path)
        nonexistent = tmp_path / "nope"
        results = loader._scan_dir(nonexistent, source="test")
        assert results == []

    def test_get_available_skills_merges_sources(self, tmp_path):
        loader = self._make_loader(tmp_path)
        local_dir = loader.project_skills_dir
        (local_dir / "local_tool.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def local_tool() -> str:\n    """Local"""\n    return "local"\n'
        )
        results = loader.get_available_skills()
        local_names = [s.name for s in results if s.source == "local"]
        assert "local_tool" in local_names

    def test_load_project_skills_builtin(self, tmp_path):
        config = ProjectConfig(skills={"file_reader": {"source": "builtin"}})
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        loader = SkillLoader(project_dir, config)
        results = loader.load_project_skills()
        assert len(results) == 1
        assert results[0].name == "file_reader"
        assert results[0].source == "builtin"

    def test_load_project_skills_unknown_raises(self, tmp_path):
        config = ProjectConfig(skills={"mystery": {"source": "unknown_source"}})
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        loader = SkillLoader(project_dir, config)
        import pytest

        with pytest.raises(ValueError, match="mystery"):
            loader.load_project_skills()

    def test_load_project_skills_git_source(self, tmp_path):
        """Git 源 Skill：从版本化缓存路径加载"""
        # 模拟全局缓存
        cache = tmp_path / "global" / "github.com" / "user" / "search" / "v1.0.0"
        cache.mkdir(parents=True)
        (cache / "skill.toml").write_text(
            'manifest_version = 1\n[skill]\nname = "search"\nversion = "1.0.0"\n'
            'description = "Search"\nentry = "skill.py"\n[permissions]\nnetwork = true\n'
        )
        (cache / "skill.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def search(query: str) -> str:\n    """Search the web"""\n    return query\n'
        )

        config = ProjectConfig(
            skills={
                "my_search": {
                    "git": "https://github.com/user/search.git",
                    "tag": "v1.0.0",
                }
            }
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)

        loader = SkillLoader(project_dir, config)
        loader.global_skills_dir = tmp_path / "global"  # override for test

        results = loader.load_project_skills()
        assert len(results) == 1
        assert results[0].name == "my_search"  # alias, not "search"
        assert results[0].source == "git"

    def test_load_project_skills_git_not_installed_raises(self, tmp_path):
        """Git 源 Skill 未安装时报错"""
        config = ProjectConfig(
            skills={
                "missing": {
                    "git": "https://github.com/user/missing.git",
                    "tag": "v1.0.0",
                }
            }
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)

        loader = SkillLoader(project_dir, config)
        loader.global_skills_dir = tmp_path / "empty_global"

        import pytest

        with pytest.raises(RuntimeError, match="未安装"):
            loader.load_project_skills()

    def test_alias_overrides_skill_name(self, tmp_path):
        """agent.toml 的 key 作为 LLM tool name"""
        config = ProjectConfig(skills={"file_reader": {"source": "builtin"}})
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        loader = SkillLoader(project_dir, config)
        results = loader.load_project_skills()
        assert results[0].name == "file_reader"

    def test_overrides_stored_on_loaded_skill(self, tmp_path):
        """Soft eject override 存储在 LoadedSkill 上"""
        config = ProjectConfig(
            skills={
                "file_reader": {
                    "source": "builtin",
                    "override": {"prompt": "用中文回答"},
                }
            }
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        loader = SkillLoader(project_dir, config)
        results = loader.load_project_skills()
        assert results[0].overrides == {"prompt": "用中文回答"}

    def test_scan_versioned_cache(self, tmp_path):
        """遍历版本化缓存目录树"""
        # 创建两个版本
        v1 = tmp_path / "github.com" / "user" / "tool" / "v1.0.0"
        v1.mkdir(parents=True)
        (v1 / "skill.toml").write_text(
            'manifest_version = 1\n[skill]\nname = "tool"\nversion = "1.0.0"\n'
            'description = "V1"\n[permissions]\n'
        )
        (v1 / "skill.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def tool_fn() -> str:\n    """V1"""\n    return "v1"\n'
        )

        v2 = tmp_path / "github.com" / "user" / "tool" / "v2.0.0"
        v2.mkdir(parents=True)
        (v2 / "skill.toml").write_text(
            'manifest_version = 1\n[skill]\nname = "tool"\nversion = "2.0.0"\n'
            'description = "V2"\n[permissions]\n'
        )
        (v2 / "skill.py").write_text(
            "from agentos.core.tool import tool\n\n@tool\n"
            'def tool_fn() -> str:\n    """V2"""\n    return "v2"\n'
        )

        config = ProjectConfig()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "agent" / "skills").mkdir(parents=True)
        loader = SkillLoader(project_dir, config)
        loader.global_skills_dir = tmp_path

        results = loader._scan_versioned_cache()
        # Should find at least the latest version
        assert len(results) >= 1
        names = [s.name for s in results]
        assert "tool" in names
