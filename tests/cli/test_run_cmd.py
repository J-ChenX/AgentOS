from unittest.mock import patch

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def _make_agent_workspace(tmp_path, toml_content=None):
    """Helper: create agent/ dir with agent.toml inside tmp_path."""
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    (agent_dir / "agent.toml").write_text(
        toml_content or '[project]\nname = "test"\n[skills]\n'
    )
    return agent_dir


class TestRunCommand:
    def test_fails_without_agent_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0 or "agent/agent.toml" in result.output

    def test_starts_server_with_agent_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_agent_workspace(tmp_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("agentos.cli.run_cmd.uvicorn") as mock_uv:
            runner.invoke(app, ["run", "--port", "9999"])
        mock_uv.run.assert_called_once()
        call_args = mock_uv.run.call_args
        assert call_args.kwargs.get("port") == 9999

    def test_dev_mode_passes_reload(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_agent_workspace(tmp_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        with patch("agentos.cli.run_cmd.uvicorn") as mock_uv:
            runner.invoke(app, ["run", "--dev"])
        call_args = mock_uv.run.call_args
        assert call_args.kwargs.get("reload") is True

    def test_loads_env_from_agent_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        agent_dir = _make_agent_workspace(tmp_path)
        (agent_dir / ".env").write_text("OPENAI_API_KEY=from-agent-dir\n")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with (
            patch("agentos.cli.run_cmd.uvicorn"),
            patch("agentos.cli.run_cmd.load_dotenv") as mock_dotenv,
        ):
            runner.invoke(app, ["run"])
        mock_dotenv.assert_called_once_with(agent_dir / ".env", override=True)

    def test_validate_api_key_fails_when_no_key_no_base_url(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_agent_workspace(
            tmp_path,
            '[project]\nname = "test"\n[llm]\nmodel = "gpt-4"\n[skills]\n',
        )
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        assert "API Key" in result.output

    def test_validate_api_key_passes_with_base_url(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _make_agent_workspace(
            tmp_path,
            '[project]\nname = "test"\n[llm]\nmodel = "gpt-4"\nbase_url = "http://localhost"\n[skills]\n',
        )
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("agentos.cli.run_cmd.uvicorn") as mock_uv:
            runner.invoke(app, ["run"])
        mock_uv.run.assert_called_once()
