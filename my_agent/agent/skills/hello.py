"""Hello Skill — 示例技能

演示标准 Skill 的编写规范。每个 Skill 函数必须包含：
1. 清晰的 docstring（描述功能、参数、返回值）
2. @tool 装饰器注册为 Agent 可调用工具

工作流程: 用户请求打招呼 → Agent 调用此技能 → 返回问候语
"""

from langchain_core.tools import tool


@tool
def hello(name: str) -> str:
    """向指定用户打招呼。

    Args:
        name: 用户的名字

    Returns:
        包含用户名字的问候语
    """
    return f"你好, {name}! 我是你的 AI 助手。"
