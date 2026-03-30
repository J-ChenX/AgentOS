# Skills 开发规范

`src/agentos/builtin_skills/` 包含随 `agentos` 包分发的内置 Skills，也是编写正确 Skill 的规范参考。

## 什么是 Skill

Skill 是一个 Python 模块，导出一个或多个用 `@tool` 装饰的函数。`@tool` 装饰器（来自 `agentos.core.tool`）将函数转换为 `ToolSpec` 对象，具备：

- **名称**：函数名（可通过 `agent.toml` 别名覆盖）
- **描述**：函数的 docstring（LLM 读取此内容决定何时调用）
- **参数 Schema**：由类型注解通过 Pydantic 自动生成的 JSON Schema
- **调用接口**：`await spec.invoke(**kwargs)` 含自动参数验证

---

## Skill 文件基本结构

```python
# skills/my_skill/skill.py
from agentos.core.tool import tool
from agentos.builtin_skills._common import get_file_scope  # 需要文件访问时引入


@tool
def my_operation(query: str, limit: int = 10) -> str:
    """一句话描述，成为 LLM 看到的工具说明。

    可选的详细说明（当前实现不传给 LLM）。
    """
    # 可选：文件访问控制
    scope = get_file_scope()
    if scope is not None:
        allowed, reason = scope.check_access(query)
        if not allowed:
            return f"访问被拒绝：{reason}"

    result = do_something(query, limit)
    return str(result)
```

### @tool 的关键规则

- **docstring 第一行**用作 LLM 工具描述，必须是清晰的祈使句
- **所有参数必须有类型注解**，未注解参数被识别为 `Any`
- **默认值**保留在 JSON Schema 中（可选参数）
- **返回类型必须为 `str`**（或可被 `str()` 转换）

### 异步 Skill

`@tool` 同时支持同步和异步函数：

```python
@tool
async def fetch_url(url: str) -> str:
    """获取指定 URL 的内容。"""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text
```

---

## Skill 目录结构

### 单文件 Skill

```
skills/
└── hello.py          # 入口就是 hello.py 本身
```

### 包目录 Skill（推荐用于复杂 Skill）

```
skills/
└── my_tool/
    ├── __init__.py    # SkillLoader 优先查找此文件
    ├── skill.py       # 或用 skill.py 作为主文件
    ├── skill.toml     # Git Skill 必须有；本地 Skill 推荐有
    ├── helpers.py     # 内部模块，不会被识别为工具
    └── requirements.txt  # 可选，本 Skill 的 pip 依赖
```

`SkillLoader._find_skill_entry()` 解析顺序：
1. 路径是 `.py` 文件 → 直接使用
2. 目录含 `__init__.py` → 使用它
3. 目录含 `skill.py` → 使用它

只有 `@tool` 装饰的 `ToolSpec` 对象会被提取，其他对象忽略。

---

## skill.toml Manifest

Git 托管或随包分发的 Skill 必须包含 `skill.toml`，项目本地 Skill 可省略。

```toml
manifest_version = 1

[skill]
name = "my-tool"          # kebab-case 标识符（与 Python 函数名无关）
version = "1.2.0"         # SemVer，用于版本显示和缓存排序
description = "一句话描述此 Skill 的功能。"
author = "your-name"
entry = "skill.py"        # 相对路径，仅供参考

[permissions]
file_read = false         # 通过 FileScope 读取文件
file_write = false        # 写入文件
network = true            # 发出 HTTP 请求
shell = false             # 执行 shell 命令
env_vars = ["MY_API_KEY"] # 此 Skill 读取的环境变量名
```

### 权限字符串映射

| TOML 字段 | 值 | 权限字符串 |
|-----------|-----|-----------|
| `file_read = true` | boolean | `"file_read"` |
| `network = true` | boolean | `"network"` |
| `env_vars = ["KEY"]` | list | `"env_vars:KEY"` |

这些字符串出现在 `agent-lock.toml` 的 `approved_permissions` 中。

---

## FileScope 集成

需要访问文件系统的 Skill 必须通过 `_common.get_file_scope()` 检查访问权限。

```python
from agentos.builtin_skills._common import get_file_scope

scope = get_file_scope()
if scope is not None:
    ok, reason = scope.check_access("data/output.csv")
    if not ok:
        return f"拒绝：{reason}"
```

**路径必须是相对字符串**（不能是绝对路径）。返回 `(True, "allowed")` 或 `(False, "<原因>")`。

**何时使用 FileScope**：
- 用户提供文件路径时，始终使用
- 硬编码内部路径（如读取打包的配置文件）时可跳过

---

## 内置 Skills 说明

### file_reader

读取项目目录内的文本文件。

- 工具函数：`read_file(file_path: str) -> str`
- 权限：`file_read = true`
- 防护：FileScope 检查、1MB 大小限制、二进制文件检测

### web_search

网页搜索（stub 实现，待接入真实 API）。

- 工具函数：`web_search(query: str) -> str`
- 权限：`network = true`、`env_vars = ["TAVILY_API_KEY"]`

### system_shell

执行 shell 命令（含危险命令黑名单）。

- 工具函数：`run_shell(command: str) -> str`
- 权限：`file_read = true`、`file_write = true`、`shell = true`
- 阻断模式：`rm -rf`、`del /s /q`、`format`、`curl | sh`、fork bomb 等
- 黑名单是尽力而为的安全措施，**不是安全边界**

---

## 新建内置 Skill 步骤

```bash
mkdir src/agentos/builtin_skills/my_skill
touch src/agentos/builtin_skills/my_skill/__init__.py
```

```python
# src/agentos/builtin_skills/my_skill/skill.py
from agentos.core.tool import tool

@tool
def my_skill(input: str) -> str:
    """一句话向 LLM 说明此 Skill 的功能。"""
    return f"结果：{input}"
```

```toml
# src/agentos/builtin_skills/my_skill/skill.toml
manifest_version = 1
[skill]
name = "my-skill"
version = "0.1.0"
description = "功能说明。"
author = "agentos-team"
entry = "skill.py"
[permissions]
file_read = false
file_write = false
network = false
shell = false
env_vars = []
```

在 `agent.toml` 中使用：
```toml
[skills]
my_skill = { source = "builtin" }
```

> **注意**：内置 Skill 的 `agent.toml` key 必须与 `builtin_skills/` 下的目录名一致。

---

## 发布 Git 托管 Skill

最小仓库结构：

```
my-search-skill/      ← Git 仓库根目录
├── skill.toml        ← 必须有
├── skill.py          ← 或 __init__.py
└── README.md
```

发布版本：
```bash
git tag v1.0.0
git push origin v1.0.0
```

在项目中添加：
```bash
agentos skill add web_search \
    --git https://github.com/my-org/my-search-skill.git \
    --tag v1.0.0
```

安装流程：clone → 读取 `skill.toml` 权限 → 提示用户审批 → 写入 `agent-lock.toml`。

---

## 本地项目 Skill

本地 Skill 放在项目 `skills/` 目录，无需 manifest：

```python
# my-agent/skills/custom_analysis.py
from agentos.core.tool import tool

@tool
def analyze_data(file_path: str, metric: str = "mean") -> str:
    """分析 CSV 文件并返回指定指标的统计数据。"""
    import csv
    from pathlib import Path
    data = Path(file_path).read_text()
    reader = csv.DictReader(data.splitlines())
    values = [float(row[metric]) for row in reader if metric in row]
    if not values:
        return f"未找到指标 '{metric}' 的数据"
    mean = sum(values) / len(values)
    return f"mean={mean:.2f}, n={len(values)}"
```

```toml
# agent.toml
[skills]
analyze_data = { path = "./skills/custom_analysis.py" }
```

---

## Soft Eject（软弹出）

无需复制源码即可定制 Skill 行为：

```toml
[skills]
file_reader = { source = "builtin", override = { prompt = "始终用中文回复。" } }
```

`override.prompt` 在加载时替换工具的 description（LLM 读取的内容）。

完整 Eject 则将源码复制到 `skills/`：

```bash
agentos skill eject file_reader
# 复制 builtin_skills/file_reader/ → skills/file_reader/
# 更新 agent.toml: file_reader = { path = "./skills/file_reader" }
```

---

## 测试 Skills

Skills 是普通 Python 函数，可直接测试，无需启动完整框架：

```python
from agentos.builtin_skills.my_skill.skill import my_skill

def test_my_skill_basic():
    result = my_skill.fn(input="hello")   # 直接调用底层函数
    assert "hello" in result

def test_my_skill_with_scope(tmp_path):
    import agentos.builtin_skills._common as common
    from agentos.core.file_scope import FileScope

    scope = FileScope(project_dir=tmp_path, allow=["./"], deny=[".env"])
    common.get_file_scope = lambda: scope
    result = my_skill.fn(input="test")
    assert result is not None
    common.get_file_scope = lambda: None  # 还原

@pytest.mark.anyio
async def test_tool_spec_validates_args():
    result = await my_skill.invoke(input="hello")  # 含 Pydantic 参数验证
    assert isinstance(result, str)
```
