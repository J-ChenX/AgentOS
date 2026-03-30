from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


class TestSkillInstall:
    def test_install_no_git_skills_does_nothing(self, tmp_path, monkeypatch):
        """只有 builtin/local skills 时 install 无操作"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\nfile_reader = { source = "builtin" }\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "install"])
        assert result.exit_code == 0
        assert "无需安装" in result.output or "完成" in result.output

    def test_install_fails_without_agent_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["skill", "install"])
        assert result.exit_code != 0 or "agent.toml" in result.output

    def test_install_calls_git_clone(self, tmp_path, monkeypatch):
        """验证 install 调用 GitInstaller.clone"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\n'
            'web = { git = "https://github.com/user/web.git", tag = "v1.0.0" }\n'
        )
        (tmp_path / "skills").mkdir()

        mock_installer = MagicMock()
        mock_installer.is_cached.return_value = False
        mock_installer.clone.return_value = (tmp_path / "cache", "abc123")
        mock_installer.read_manifest.return_value = {
            "skill": {"name": "web", "version": "1.0.0"},
            "permissions": {"network": True},
        }
        mock_installer.extract_permissions.return_value = ["network"]

        with patch("agentos.cli.skill_cmd.GitInstaller", return_value=mock_installer):
            runner.invoke(app, ["skill", "install"], input="Y\n")

        mock_installer.clone.assert_called_once()

    def test_install_skips_cached_with_matching_commit(self, tmp_path, monkeypatch):
        """已缓存且 commit 匹配时跳过"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\n'
            'web = { git = "https://github.com/user/web.git", tag = "v1.0.0" }\n'
        )
        (tmp_path / "skills").mkdir()

        # Pre-create lock file with matching commit
        (tmp_path / "agent-lock.toml").write_text(
            '[locks.web]\ngit = "https://github.com/user/web.git"\ntag = "v1.0.0"\n'
            'commit = "abc123"\nresolved_path = "x"\napproved_permissions = ["network"]\n'
        )

        mock_installer = MagicMock()
        mock_installer.is_cached.return_value = True
        mock_installer.get_cached_commit.return_value = "abc123"

        with patch("agentos.cli.skill_cmd.GitInstaller", return_value=mock_installer):
            runner.invoke(app, ["skill", "install"])

        mock_installer.clone.assert_not_called()
