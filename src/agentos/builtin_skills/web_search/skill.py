"""Web Search Skill — 通过 Tavily API 搜索互联网"""

from __future__ import annotations

import os

from agentos.core.tool import tool


def _tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Call Tavily Search API. Returns list of {title, url, content}."""
    import json as json_mod
    import urllib.error
    import urllib.request

    api_key = os.environ["TAVILY_API_KEY"]
    payload = json_mod.dumps(
        {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json_mod.loads(resp.read())

    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in data.get("results", [])
    ]


@tool
def web_search(query: str) -> str:
    """搜索互联网获取信息。返回搜索结果标题、摘要和链接。"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误：未配置 TAVILY_API_KEY 环境变量。请在 .env 文件中设置。"

    try:
        results = _tavily_search(query)
    except Exception as e:
        return f"错误：搜索失败 — {e}"

    if not results:
        return f"未找到与 '{query}' 相关的结果"

    output = []
    for i, r in enumerate(results, 1):
        output.append(f"{i}. **{r['title']}**\n   {r['url']}\n   {r['content']}\n")

    return "\n".join(output)
