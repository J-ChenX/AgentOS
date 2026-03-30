from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


class TestSkillRemove:
    def test_removes_from_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n\n[skills]\nweb = { source = "builtin" }\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "remove", "web"])
        assert result.exit_code == 0
        content = (tmp_path / "agent.toml").read_text()
        assert "web" not in content or "移除" in result.output

    def test_removes_lock_entry(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n\n[skills]\n'
            'web = { git = "https://github.com/user/web.git", tag = "v1.0.0" }\n'
        )
        (tmp_path / "agent-lock.toml").write_text(
            '[locks.web]\ngit = "https://github.com/user/web.git"\ntag = "v1.0.0"\n'
            'commit = "abc"\nresolved_path = "x"\napproved_permissions = []\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "remove", "web"])
        assert result.exit_code == 0
        if (tmp_path / "agent-lock.toml").exists():
            lock_content = (tmp_path / "agent-lock.toml").read_text()
            assert "web" not in lock_content or "[locks]" not in lock_content


class TestSkillUpdate:
    def test_update_same_tag_no_op(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\n'
            'web = { git = "https://github.com/user/web.git", tag = "v1.0.0" }\n'
        )
        (tmp_path / "agent-lock.toml").write_text(
            '[locks.web]\ngit = "https://github.com/user/web.git"\ntag = "v1.0.0"\n'
            'commit = "abc"\nresolved_path = "x"\napproved_permissions = []\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "update", "web"])
        assert result.exit_code == 0
        assert "最新版本" in result.output or "无需更新" in result.output

    def test_update_non_git_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\nreader = { source = "builtin" }\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "update", "reader"])
        assert result.exit_code != 0 or "Git 引用" in result.output


class TestSkillInfo:
    def test_shows_builtin_info(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text(
            '[project]\nname = "t"\n[skills]\nfile_reader = { source = "builtin" }\n'
        )
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "info", "file_reader"])
        assert result.exit_code == 0
        assert "file_reader" in result.output or "file-reader" in result.output

    def test_info_unknown_skill_errors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent.toml").write_text('[project]\nname = "t"\n[skills]\n')
        (tmp_path / "skills").mkdir()
        result = runner.invoke(app, ["skill", "info", "nonexistent"])
        assert result.exit_code != 0 or "未找到" in result.output
