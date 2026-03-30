"""Tests for create_app() CWD-reading engine factory."""

AGENT_TOML_LOCAL = """\
[project]
name = "test-agent"

[llm]
model = "gpt-4"
base_url = "http://localhost:11434"

[skills]
"""


def _setup_agent_dir(tmp_path, toml_content=AGENT_TOML_LOCAL):
    """Create agent/agent.toml in tmp_path."""
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    (agent_dir / "agent.toml").write_text(toml_content)
    return agent_dir


class TestEngineWiring:
    def test_create_app_without_agent_toml_uses_stub_engine(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from agentos.server.app import create_app
        from agentos.server.stub_engine import StubEngine

        app = create_app()
        assert isinstance(app.state.engine, StubEngine)

    def test_create_app_with_agent_dir_uses_agent_runner(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _setup_agent_dir(tmp_path)
        from agentos.core.runner import AgentRunner
        from agentos.server.app import create_app

        app = create_app()
        assert isinstance(app.state.engine, AgentRunner)

    def test_create_app_engine_mounted_to_app_state(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from agentos.server.app import create_app

        app = create_app()
        assert hasattr(app.state, "engine")
        assert app.state.engine is not None

    def test_create_app_agent_runner_has_correct_model(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _setup_agent_dir(tmp_path)
        from agentos.core.runner import AgentRunner
        from agentos.server.app import create_app

        app = create_app()
        assert isinstance(app.state.engine, AgentRunner)
        assert app.state.engine.llm_config.model == "gpt-4"

    def test_create_app_skill_loader_failure_degrades_to_empty_tools(self, tmp_path, monkeypatch):
        """Bad skill path in agent.toml → warns, but AgentRunner still created."""
        monkeypatch.chdir(tmp_path)
        bad_toml = AGENT_TOML_LOCAL + 'bad = {path = "nonexistent/"}\n'
        _setup_agent_dir(tmp_path, bad_toml)
        from agentos.core.runner import AgentRunner
        from agentos.server.app import create_app

        app = create_app()
        assert isinstance(app.state.engine, AgentRunner)
