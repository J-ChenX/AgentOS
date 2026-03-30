import json

from agentos.builtin_skills.todo_manager.skill import update_todos


class TestUpdateTodos:
    def test_returns_todos_updated_action(self):
        todos = json.dumps(
            [
                {"content": "Write tests", "status": "completed"},
                {"content": "Implement feature", "status": "in_progress"},
            ]
        )
        result = update_todos(todos)
        parsed = json.loads(result)
        assert parsed["_action"] == "todos_updated"
        assert len(parsed["todos"]) == 2

    def test_invalid_json_returns_error(self):
        result = update_todos("not json")
        assert "错误" in result

    def test_empty_list(self):
        result = update_todos("[]")
        parsed = json.loads(result)
        assert parsed["_action"] == "todos_updated"
        assert parsed["todos"] == []

    def test_validates_status_values(self):
        todos = json.dumps([{"content": "task", "status": "invalid_status"}])
        result = update_todos(todos)
        assert "错误" in result
