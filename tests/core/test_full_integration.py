"""Integration test: verify all 10 builtin skills load and their tools are accessible."""

import pytest

from agentos.core.project_config import ProjectConfig
from agentos.core.skill_loader import SkillLoader


@pytest.fixture
def full_config(tmp_path):
    """Create an agent.toml with all 10 skills enabled."""
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    toml_content = """\
[project]
name = "test"
version = "0.1.0"

[llm]
model = "test-model"

[agent]
type = "react"

[scope]
allow = ["./"]

[skills]
file_reader = { source = "builtin" }
file_writer = { source = "builtin" }
file_editor = { source = "builtin" }
file_search = { source = "builtin" }
content_search = { source = "builtin" }
system_shell = { source = "builtin" }
web_search = { source = "builtin" }
ask_user = { source = "builtin" }
todo_manager = { source = "builtin" }
memory_writer = { source = "builtin" }
"""
    (agent_dir / "agent.toml").write_text(toml_content, encoding="utf-8")
    return tmp_path, agent_dir


def test_all_10_skills_load(full_config):
    """All 10 builtin skills should load without error."""
    project_dir, agent_dir = full_config
    config = ProjectConfig.from_toml(agent_dir / "agent.toml")
    loader = SkillLoader(project_dir, config)
    loaded = loader.load_project_skills()

    skill_names = {s.name for s in loaded}
    expected = {
        "file_reader",
        "file_writer",
        "file_editor",
        "file_search",
        "content_search",
        "system_shell",
        "web_search",
        "ask_user",
        "todo_manager",
        "memory_writer",
    }
    assert skill_names == expected


def test_all_tools_have_valid_schemas(full_config):
    """Every tool function should produce a valid OpenAI tool schema."""
    project_dir, agent_dir = full_config
    config = ProjectConfig.from_toml(agent_dir / "agent.toml")
    loader = SkillLoader(project_dir, config)
    loaded = loader.load_project_skills()

    for skill in loaded:
        for tool_fn in skill.tool_functions:
            schema = tool_fn.to_openai_schema()
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
            # Internal params should not appear
            for prop_name in schema["function"]["parameters"].get("properties", {}):
                assert not prop_name.startswith("_"), (
                    f"Internal param {prop_name} leaked in {tool_fn.name}"
                )
