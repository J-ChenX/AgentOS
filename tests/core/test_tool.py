import pytest

from agentos.core.tool import ToolSpec, tool


class TestToolDecorator:
    def test_basic_tool_creation(self):
        @tool
        def greet(name: str) -> str:
            """Say hello"""
            return f"hi {name}"

        assert isinstance(greet, ToolSpec)
        assert greet.name == "greet"
        assert greet.description == "Say hello"

    def test_parameters_schema(self):
        @tool
        def greet(name: str) -> str:
            """Say hello"""
            return f"hi {name}"

        schema = greet.parameters
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "name" in schema["required"]

    def test_optional_param_not_required(self):
        @tool
        def search(query: str, limit: int = 10) -> str:
            """Search"""
            return query

        assert "query" in search.parameters["required"]
        assert "limit" not in search.parameters["required"]

    def test_to_openai_schema(self):
        @tool
        def greet(name: str) -> str:
            """Say hello"""
            return f"hi {name}"

        schema = greet.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "greet"
        assert schema["function"]["description"] == "Say hello"

    @pytest.mark.anyio
    async def test_invoke_sync_fn(self):
        @tool
        def add(a: int, b: int) -> str:
            """Add numbers"""
            return str(a + b)

        result = await add.invoke(a=1, b=2)
        assert result == "3"

    @pytest.mark.anyio
    async def test_invoke_async_fn(self):
        @tool
        async def fetch(url: str) -> str:
            """Fetch URL"""
            return f"fetched {url}"

        result = await fetch.invoke(url="https://example.com")
        assert result == "fetched https://example.com"

    @pytest.mark.anyio
    async def test_invoke_validates_args(self):
        @tool
        def add(a: int, b: int) -> str:
            """Add"""
            return str(a + b)

        result = await add.invoke(a="not_a_number", b=2)
        assert "校验失败" in result

    def test_description_mutable_for_soft_eject(self):
        @tool
        def greet(name: str) -> str:
            """Say hello"""
            return f"hi {name}"

        greet.description = "Modified description"
        assert greet.description == "Modified description"
        assert greet.to_openai_schema()["function"]["description"] == "Modified description"

    def test_underscore_params_excluded_from_schema(self):
        @tool
        def dangerous_op(command: str, _confirmed: bool = False) -> str:
            """Run something"""
            return command

        schema = dangerous_op.parameters
        assert "command" in schema["properties"]
        assert "_confirmed" not in schema["properties"]
        assert "command" in schema["required"]
        # _confirmed should still work when invoked directly
        assert dangerous_op.fn("ls", _confirmed=True) == "ls"

    @pytest.mark.anyio
    async def test_underscore_params_passable_via_invoke(self):
        @tool
        def op(name: str, _internal: bool = False) -> str:
            """Op"""
            return f"{name}:{_internal}"

        result = await op.invoke(name="test", _internal=True)
        assert result == "test:True"
