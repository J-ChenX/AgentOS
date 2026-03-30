import json

from agentos.core.tool import tool


@tool
def ask_user(question: str, options: str = "") -> str:
    """向用户提问并等待回答。options 为可选的选项列表（逗号分隔），留空则为开放式提问。
    调用后 Agent 将暂停执行，等待用户通过界面回答。"""
    option_list = [o.strip() for o in options.split(",") if o.strip()] if options else []
    return json.dumps(
        {"_action": "ask_user", "question": question, "options": option_list},
        ensure_ascii=False,
    )
