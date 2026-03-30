from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


class TestInitCommand:
    def test_creates_project_with_agent_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "my-agent"])
        assert result.exit_code == 0
        assert (tmp_path / "my-agent").is_dir()
        assert (tmp_path / "my-agent" / "agent").is_dir()

    def test_creates_agent_toml_inside_agent_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        toml_path = tmp_path / "test-proj" / "agent" / "agent.toml"
        assert toml_path.exists()
        content = toml_path.read_text(encoding="utf-8")
        assert 'name = "test-proj"' in content
        assert "[skills]" in content
        assert "system_prompt_path" in content
        assert "memory_path" in content

    def test_creates_agent_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        agent_md = tmp_path / "test-proj" / "agent" / "agent.md"
        assert agent_md.exists()
        content = agent_md.read_text(encoding="utf-8")
        assert "记忆系统管理规范" in content
        assert "replace_section" in content
        assert "memory_store" in content

    def test_creates_memory_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        memory_md = tmp_path / "test-proj" / "agent" / "memory.md"
        assert memory_md.exists()
        content = memory_md.read_text(encoding="utf-8")
        assert "## 用户偏好" in content
        assert "## 项目规范" in content
        assert "## 知识库索引" in content

    def test_creates_env_example(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        env_example = tmp_path / "test-proj" / "agent" / ".env.example"
        assert env_example.exists()
        assert "LLM_API_KEY" in env_example.read_text(encoding="utf-8")

    def test_creates_skills_dir_with_hello(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        hello = tmp_path / "test-proj" / "agent" / "skills" / "hello.py"
        assert hello.exists()
        content = hello.read_text(encoding="utf-8")
        assert "@tool" in content
        assert "def hello(name: str) -> str:" in content
        assert '"""向指定用户打招呼。' in content

    def test_does_not_create_old_dirs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        proj = tmp_path / "test-proj"
        assert not (proj / "docs").exists()
        assert not (proj / "records").exists()
        assert not (proj / "templates").exists()
        assert not (proj / "skills").exists()
        assert not (proj / ".agentignore").exists()
        assert not (proj / "agent.toml").exists()

    def test_does_not_create_memory_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        assert not (tmp_path / "test-proj" / "agent" / "memory_store").exists()

    def test_creates_gitignore_with_agent_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "test-proj"])
        gitignore = tmp_path / "test-proj" / ".gitignore"
        assert gitignore.exists()
        assert "agent/.env" in gitignore.read_text(encoding="utf-8")

    def test_appends_to_existing_gitignore(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        proj = tmp_path / "test-proj"
        proj.mkdir()
        (proj / ".gitignore").write_text("node_modules/\n")
        runner.invoke(app, ["init", "test-proj"])
        content = (proj / ".gitignore").read_text(encoding="utf-8")
        assert "node_modules/" in content
        assert "agent/.env" in content

    def test_does_not_duplicate_gitignore_entry(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        proj = tmp_path / "test-proj"
        proj.mkdir()
        (proj / ".gitignore").write_text("agent/.env\n")
        runner.invoke(app, ["init", "test-proj"])
        content = (proj / ".gitignore").read_text(encoding="utf-8")
        assert content.count("agent/.env") == 1

    def test_fails_if_agent_dir_has_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        proj = tmp_path / "existing"
        (proj / "agent").mkdir(parents=True)
        (proj / "agent" / "agent.toml").write_text('[project]\nname = "existing"\n')
        result = runner.invoke(app, ["init", "existing"])
        assert result.exit_code != 0 or "已是 Agent 项目" in result.output

    def test_auto_detects_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "GEMINI_BASE_URL=https://api.example.com/v1\nGEMINI_MODEL=gemini-pro\n"
        )
        runner.invoke(app, ["init", "test-proj"])
        toml_content = (tmp_path / "test-proj" / "agent" / "agent.toml").read_text(
            encoding="utf-8"
        )
        assert "gemini-pro" in toml_content
        assert "https://api.example.com/v1" in toml_content


def test_init_creates_all_default_skills(tmp_path, monkeypatch):
    import contextlib
    monkeypatch.chdir(tmp_path)
    from agentos.cli.init_cmd import init_command
    with contextlib.suppress(SystemExit):
        init_command("test_project")
    agent_toml = tmp_path / "test_project" / "agent" / "agent.toml"
    content = agent_toml.read_text(encoding="utf-8")
    for skill_name in [
        "file_reader", "file_writer", "file_editor", "file_search",
        "content_search", "system_shell", "web_search", "ask_user",
        "todo_manager", "memory_writer",
    ]:
        assert skill_name in content, f"Missing skill: {skill_name}"
    assert "safe_commands" in content
    assert "confirm_mode" in content


def test_init_agent_md_has_tool_rules(tmp_path, monkeypatch):
    import contextlib
    monkeypatch.chdir(tmp_path)
    from agentos.cli.init_cmd import init_command
    with contextlib.suppress(SystemExit):
        init_command("test_project2")
    agent_md = tmp_path / "test_project2" / "agent" / "agent.md"
    content = agent_md.read_text(encoding="utf-8")
    assert "工具使用规则" in content
    assert "read_file" in content
    assert "edit_file" in content
    assert "expected_snippet" in content
