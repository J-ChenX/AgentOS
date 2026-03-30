from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


class TestSkillList:
    def test_lists_builtin_skills(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n[skills]\n')
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "list"])
        assert result.exit_code == 0
        assert "file_reader" in result.output

    def test_list_shows_version_column(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n[skills]\n')
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "list"])
        assert result.exit_code == 0
        assert "版本" in result.output


class TestSkillAdd:
    def test_adds_skill_to_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n\n[skills]\n')
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "add", "web_search"])
        assert result.exit_code == 0
        content = (tmp_path / "agent.toml").read_text()
        assert "web_search" in content

    def test_add_nonexistent_skill_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n\n[skills]\n')
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "add", "nonexistent_xyz"])
        assert "未找到" in result.output or result.exit_code != 0

    def test_add_with_git_and_tag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n\n[skills]\n')
        (tmp_path / "skills").mkdir()

        mock_installer = MagicMock()
        mock_installer.is_cached.return_value = False
        mock_installer.clone.return_value = (tmp_path / "cache", "abc123")
        mock_installer.read_manifest.return_value = {
            "skill": {"name": "web", "version": "1.0.0"},
            "permissions": {},
        }
        mock_installer.extract_permissions.return_value = []

        with patch("agentos.cli.skill_cmd.GitInstaller", return_value=mock_installer):
            result = runner.invoke(
                app,
                [
                    "skill",
                    "add",
                    "my_web",
                    "--git",
                    "https://github.com/user/web.git",
                    "--tag",
                    "v1.0.0",
                ],
            )

        assert result.exit_code == 0
        content = (tmp_path / "agent.toml").read_text()
        assert "my_web" in content
        assert "github.com" in content


class TestSkillEject:
    def test_ejects_builtin_to_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n\n[skills]\nfile_reader = { source = "builtin" }\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "eject", "file_reader"])
        assert result.exit_code == 0
        assert (tmp_path / "skills" / "file_reader").is_dir()
        content = (tmp_path / "agent.toml").read_text()
        assert "path" in content

    def test_eject_already_local_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n\n[skills]\n')
        local_dir = tmp_path / "skills" / "file_reader"
        local_dir.mkdir(parents=True)
        (local_dir / "skill.py").write_text("# local")
        result = runner.invoke(app, ["skill", "eject", "file_reader"])
        assert "已在本地" in result.output or result.exit_code != 0

    def test_ejects_git_source_to_local(self, tmp_path, monkeypatch):
        """从 Git 缓存 eject 到本地"""
        monkeypatch.chdir(tmp_path)

        # 模拟全局缓存
        cache_dir = tmp_path / "global_cache" / "github.com" / "user" / "web" / "v1.0.0"
        cache_dir.mkdir(parents=True)
        (cache_dir / "skill.py").write_text("# git skill code")
        (cache_dir / "skill.toml").write_text(
            '[skill]\nname = "web"\nversion = "1.0.0"\n[permissions]\n'
        )
        (cache_dir / "__init__.py").write_text("")

        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n\n[skills]\n'
            'web = { git = "https://github.com/user/web.git", tag = "v1.0.0" }\n'
        )
        (tmp_path / "skills").mkdir()

        with patch("agentos.cli.skill_cmd.GitInstaller") as MockInstaller:
            mock_inst = MockInstaller.return_value
            mock_inst.get_cache_path.return_value = cache_dir
            result = runner.invoke(app, ["skill", "eject", "web"])

        assert result.exit_code == 0
        assert (tmp_path / "skills" / "web").is_dir()
        content = (tmp_path / "agent.toml").read_text()
        assert "path" in content
