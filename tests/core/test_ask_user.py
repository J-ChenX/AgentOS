import json

from agentos.builtin_skills.ask_user.skill import ask_user


class TestAskUser:
    def test_returns_action_json_open_question(self):
        result = ask_user("What should I do?")
        parsed = json.loads(result)
        assert parsed["_action"] == "ask_user"
        assert parsed["question"] == "What should I do?"
        assert parsed["options"] == []

    def test_returns_action_json_with_options(self):
        result = ask_user("Which one?", options="A,B,C")
        parsed = json.loads(result)
        assert parsed["options"] == ["A", "B", "C"]

    def test_strips_option_whitespace(self):
        result = ask_user("Pick:", options=" yes , no ")
        parsed = json.loads(result)
        assert parsed["options"] == ["yes", "no"]

    def test_empty_options_string(self):
        result = ask_user("Free text?", options="")
        parsed = json.loads(result)
        assert parsed["options"] == []
