import json

from agentos.core.tool import tool

VALID_STATUSES = {"pending", "in_progress", "completed"}


@tool
def update_todos(todos_json: str) -> str:
    """更新当前任务列表。todos_json 为 JSON 数组，每项包含：
    - content: 任务描述
    - status: pending | in_progress | completed
    同时推送到前端并持久化到 memory_store/todos.json。"""
    try:
        todos = json.loads(todos_json)
    except json.JSONDecodeError:
        return "错误：todos_json 不是有效的 JSON"

    if not isinstance(todos, list):
        return "错误：todos_json 必须是 JSON 数组"

    for item in todos:
        if not isinstance(item, dict):
            return "错误：每个 todo 必须是对象"
        if "content" not in item or "status" not in item:
            return "错误：每个 todo 必须包含 content 和 status 字段"
        if item["status"] not in VALID_STATUSES:
            return f"错误：无效的 status '{item['status']}'，有效值为 {VALID_STATUSES}"

    return json.dumps(
        {"_action": "todos_updated", "todos": todos},
        ensure_ascii=False,
    )
