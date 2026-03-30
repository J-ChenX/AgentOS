from unittest.mock import patch

from agentos.builtin_skills.web_search.skill import web_search


class TestWebSearch:
    def test_no_api_key_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            result = web_search("test query")
            assert "TAVILY_API_KEY" in result

    @patch("agentos.builtin_skills.web_search.skill._tavily_search")
    def test_returns_formatted_results(self, mock_search):
        mock_search.return_value = [
            {"title": "Result 1", "url": "https://example.com/1", "content": "Summary 1"},
            {"title": "Result 2", "url": "https://example.com/2", "content": "Summary 2"},
        ]
        with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
            result = web_search("test query")
        assert "Result 1" in result
        assert "https://example.com/1" in result
        assert "Summary 1" in result

    @patch("agentos.builtin_skills.web_search.skill._tavily_search")
    def test_handles_api_error(self, mock_search):
        mock_search.side_effect = Exception("API error")
        with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
            result = web_search("test query")
        assert "错误" in result
