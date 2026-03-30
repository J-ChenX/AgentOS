from agentos.builtin_skills._common import (
    _file_scope_var,
    _skill_config_var,
    get_file_scope,
    get_skill_config,
)


class TestContextVarFileScope:
    def test_get_file_scope_returns_none_by_default(self):
        token = _file_scope_var.set(None)
        try:
            assert get_file_scope() is None
        finally:
            _file_scope_var.reset(token)

    def test_get_file_scope_returns_injected_value(self, tmp_path):
        from agentos.core.file_scope import FileScope

        scope = FileScope(tmp_path, allow=["./"], deny=[])
        token = _file_scope_var.set(scope)
        try:
            assert get_file_scope() is scope
        finally:
            _file_scope_var.reset(token)

    def test_reset_restores_none(self, tmp_path):
        from agentos.core.file_scope import FileScope

        scope = FileScope(tmp_path, allow=["./"], deny=[])
        token = _file_scope_var.set(scope)
        _file_scope_var.reset(token)
        assert get_file_scope() is None


class TestSkillConfigVar:
    def test_returns_empty_dict_by_default(self):
        assert get_skill_config("system_shell") == {}

    def test_returns_config_when_set(self):
        config = {"system_shell": {"safe_commands": ["ls", "pwd"], "confirm_mode": "unsafe"}}
        token = _skill_config_var.set(config)
        try:
            result = get_skill_config("system_shell")
            assert result == {"safe_commands": ["ls", "pwd"], "confirm_mode": "unsafe"}
        finally:
            _skill_config_var.reset(token)

    def test_returns_empty_dict_for_unknown_skill(self):
        config = {"system_shell": {"confirm_mode": "unsafe"}}
        token = _skill_config_var.set(config)
        try:
            assert get_skill_config("file_reader") == {}
        finally:
            _skill_config_var.reset(token)
