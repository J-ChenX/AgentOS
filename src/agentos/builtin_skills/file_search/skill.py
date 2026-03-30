import base64
from pathlib import Path

from agentos.builtin_skills._common import get_file_scope
from agentos.core.tool import tool

EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".mypy_cache"}
MAX_RESULTS = 200
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_MAX_AUTO_IMAGES = 5
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}
_MAX_PX = 2048


def _prepare_image(data: bytes, ext: str) -> tuple[bytes, str]:
    """若图片最长边超过 _MAX_PX 则缩放，返回 (bytes, media_type)。PIL 懒加载。"""
    import io  # noqa: PLC0415

    from PIL import Image  # noqa: PLC0415

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if max(w, h) > _MAX_PX:
        scale = _MAX_PX / max(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        has_alpha = img.mode in ("RGBA", "LA", "PA") or (
            img.mode == "P" and "transparency" in img.info
        )
        buf = io.BytesIO()
        if has_alpha:
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), "image/png"
        else:
            img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
            return buf.getvalue(), "image/jpeg"
    return data, _MEDIA_TYPES.get(ext, "image/png")


def _embed_image(abs_path: Path) -> list:
    """Read, optionally resize, and return multimodal content blocks for an image."""
    try:
        data = abs_path.read_bytes()
        data, media_type = _prepare_image(data, abs_path.suffix.lower())
        b64 = base64.standard_b64encode(data).decode("ascii")
        return [
            {"type": "text", "text": f"图片文件：{abs_path}"},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]
    except Exception as e:
        return [{"type": "text", "text": f"图片文件（读取失败：{e}）：{abs_path}"}]


def _to_primary_pattern(pattern: str) -> str:
    """将用户输入转成递归 glob 模式。

    规则：
    - 已含 ** 或绝对路径 → 原样返回
    - 最后一段有文件扩展名（如 foo.png）→ **/pattern
    - 其余（目录名/目录路径）→ **/clean/*
    """
    norm = pattern.replace("\\", "/").strip("/")
    if "**" in norm or Path(pattern).is_absolute():
        return pattern
    last = norm.rsplit("/", 1)[-1]
    # 有扩展名且不是纯通配符（如 *.png 也算有扩展名）
    has_ext = "." in last.lstrip(".") and not last.endswith("/*")
    if has_ext:
        return f"**/{norm}"
    clean = norm.rstrip("/*")
    return f"**/{clean}/*"


def _to_fuzzy_patterns(pattern: str) -> list[str]:
    """当递归搜索仍无结果时，取路径末尾两段做模糊匹配。

    例：图片描述/0c67975...526...png（文件名打错）
      → **/图片描述/*  +  **/*0c67975*.png（取前缀模糊匹配）
    绝对路径或已含 ** 的模式不做模糊处理。
    """
    if Path(pattern).is_absolute() or "**" in pattern:
        return []
    norm = pattern.replace("\\", "/").strip("/*")
    parts = [p for p in norm.split("/") if p and p not in (".", "..")]
    # Only use the last 2 components (most specific: parent dir + filename)
    parts = parts[-2:]
    patterns = []
    for part in parts:
        stem = Path(part).stem
        ext = Path(part).suffix
        if ext and stem:
            prefix = stem[: max(4, len(stem) // 2)]
            patterns.append(f"**/*{prefix}*{ext}")
        elif part and "*" not in part:
            patterns.append(f"**/*{part}*/*")
    return patterns


@tool
def glob_files(pattern: str, path: str = "./") -> str | list:
    """用 glob 模式搜索文件。支持 **/*.py 等递归模式。返回匹配的文件路径列表。
    若搜索结果全为图片文件（≤5张），直接返回图片内容供模型查看，无需再调用 read_file。"""
    scope = get_file_scope()
    base = Path(path).resolve()
    if not base.exists():
        return f"错误：路径 '{path}' 不存在"

    def _collect(pat: str) -> list[Path]:
        result = []
        try:
            for p in sorted(base.glob(pat)):
                if any(part in EXCLUDED_DIRS for part in p.parts):
                    continue
                if not p.is_file():
                    continue
                rel = str(p.relative_to(base)).replace("\\", "/")
                if scope is not None:
                    allowed, _ = scope.check_access(rel)
                    if not allowed:
                        continue
                result.append(p.resolve())
                if len(result) >= MAX_RESULTS:
                    break
        except Exception:
            pass
        return result

    # 1. 用智能递归模式搜索
    matches = _collect(_to_primary_pattern(pattern))

    # 2. 仍无结果 → 拆分各段做模糊搜索，合并去重
    if not matches:
        seen: set[Path] = set()
        for fuzzy_pat in _to_fuzzy_patterns(pattern):
            for p in _collect(fuzzy_pat):
                if p not in seen:
                    seen.add(p)
                    matches.append(p)

    if not matches:
        return f"未找到匹配 '{pattern}' 的文件"

    image_matches = [p for p in matches if p.suffix.lower() in _IMAGE_EXTS]
    all_images = len(matches) == len(image_matches)

    # All results are images and few enough — embed them directly so the model
    # receives the image content in this single tool call, no follow-up needed.
    if all_images and len(image_matches) <= _MAX_AUTO_IMAGES:
        blocks: list = []
        for img_path in image_matches:
            blocks.extend(_embed_image(img_path))
        return blocks

    rel_paths = [str(p.relative_to(base)).replace("\\", "/") for p in matches]
    result = "\n".join(rel_paths)
    if len(matches) >= MAX_RESULTS:
        result += f"\n\n⚠ 结果已截断（显示前 {MAX_RESULTS} 条），请缩小搜索范围。"
    return result
