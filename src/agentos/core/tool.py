"""自定义 Tool 协议 — 原生 Python + Pydantic，面向 MCP"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError, create_model

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ToolSpec:
    """工具规格定义，兼容 OpenAI Function Calling 格式"""

    name: str
    description: str
    parameters: dict  # JSON Schema（由 Pydantic 生成）
    fn: Callable[..., Any]
    pydantic_model: Any = None

    def to_openai_schema(self) -> dict:
        """转换为 OpenAI tools 参数格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __call__(self, *args, **kwargs):
        """直接调用底层函数（用于测试和同步场景）"""
        return self.fn(*args, **kwargs)

    async def invoke(self, **kwargs) -> str | list:
        """执行工具，Pydantic 校验后调用"""
        # Separate internal (_-prefixed) params from schema-validated params
        internal_kwargs = {k: v for k, v in kwargs.items() if k.startswith("_")}
        schema_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_")}

        if self.pydantic_model:
            try:
                validated_args = self.pydantic_model(**schema_kwargs).model_dump()
            except ValidationError as e:
                return f"参数校验失败: {e.errors()}"
        else:
            validated_args = schema_kwargs

        validated_args.update(internal_kwargs)
        result = self.fn(**validated_args)
        if inspect.isawaitable(result):
            result = await result
        # list = multimodal content blocks, pass through as-is
        if isinstance(result, list):
            return result
        return str(result) if not isinstance(result, str) else result


def tool(fn: Callable) -> ToolSpec:
    """装饰器 — 基于 Pydantic 从函数签名自动生成 ToolSpec"""
    sig = inspect.signature(fn)
    fields: dict[str, tuple] = {}

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        if param_name.startswith("_"):
            continue  # Internal params (e.g. _confirmed) hidden from LLM schema
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[param_name] = (annotation, default)

    model_name = f"{fn.__name__.capitalize()}Schema"
    DynamicModel = create_model(model_name, **fields)

    schema = DynamicModel.model_json_schema()
    schema.pop("title", None)

    return ToolSpec(
        name=fn.__name__,
        description=inspect.getdoc(fn) or "",
        parameters=schema,
        fn=fn,
        pydantic_model=DynamicModel,
    )
