from agentos.core.project_config import ProjectConfig


class TestProjectConfig:
    def test_from_toml_parses_all_sections(self, tmp_path):
        toml_content = """
[project]
name = "test-agent"
version = "0.2.0"

[llm]
model = "gemini-2.0-flash"
base_url = "https://api.example.com/v1"

[agent]
type = "react"
max_iterations = 30

[scope]
allow = ["./"]
deny = [".env"]

[skills]
file_reader = { source = "builtin" }
my_tool = { path = "./skills/my_tool" }
"""
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text(toml_content)
        config = ProjectConfig.from_toml(toml_file)
        assert config.name == "test-agent"
        assert config.version == "0.2.0"
        assert config.llm.model == "gemini-2.0-flash"
        assert config.llm.base_url == "https://api.example.com/v1"
        assert config.agent_type == "react"
        assert config.max_iterations == 30
        assert config.skills["file_reader"] == {"source": "builtin"}
        assert config.skills["my_tool"] == {"path": "./skills/my_tool"}

    def test_from_toml_defaults(self, tmp_path):
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text('[project]\nname = "minimal"\n')
        config = ProjectConfig.from_toml(toml_file)
        assert config.name == "minimal"
        assert config.version == "0.1.0"
        assert config.agent_type == "react"
        assert config.max_iterations == 20
        assert config.skills == {}

    def test_from_toml_file_not_found(self, tmp_path):
        import pytest

        with pytest.raises(FileNotFoundError):
            ProjectConfig.from_toml(tmp_path / "nonexistent.toml")

    def test_from_toml_parses_scope(self, tmp_path):
        toml_content = """
[project]
name = "scoped"

[scope]
allow = ["./src", "./docs"]
deny = [".env", "*.key", "secrets/"]
"""
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text(toml_content)
        config = ProjectConfig.from_toml(toml_file)
        assert config.scope_allow == ["./src", "./docs"]
        assert config.scope_deny == [".env", "*.key", "secrets/"]

    def test_from_toml_scope_defaults(self, tmp_path):
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text('[project]\nname = "no-scope"\n')
        config = ProjectConfig.from_toml(toml_file)
        assert config.scope_allow == ["./"]
        assert config.scope_deny == []

    def test_from_toml_parses_agent_prompt_and_memory_paths(self, tmp_path):
        toml_content = """
[project]
name = "paths-test"

[agent]
type = "react"
max_iterations = 20
system_prompt_path = "agent.md"
memory_path = "memory.md"
"""
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text(toml_content)
        config = ProjectConfig.from_toml(toml_file)
        assert config.system_prompt_path == "agent.md"
        assert config.memory_path == "memory.md"

    def test_from_toml_prompt_and_memory_paths_default(self, tmp_path):
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text('[project]\nname = "no-paths"\n')
        config = ProjectConfig.from_toml(toml_file)
        assert config.system_prompt_path == "agent.md"
        assert config.memory_path == "memory.md"

    def test_from_toml_git_skill_config(self, tmp_path):
        toml_content = """
[project]
name = "git-test"

[skills]
web_search = { git = "https://github.com/agentos-team/web-search.git", tag = "v1.2.0" }
local_tool = { path = "./skills/local_tool" }
reader = { source = "builtin", override = { prompt = "用中文回答" } }
"""
        toml_file = tmp_path / "agent.toml"
        toml_file.write_text(toml_content, encoding="utf-8")
        config = ProjectConfig.from_toml(toml_file)
        assert (
            config.skills["web_search"]["git"] == "https://github.com/agentos-team/web-search.git"
        )
        assert config.skills["web_search"]["tag"] == "v1.2.0"
        assert config.skills["reader"]["override"] == {"prompt": "用中文回答"}
