from __future__ import annotations

import base64
from pathlib import Path

from agentos.builtin_skills._common import get_file_scope
from agentos.core.tool import tool

# 模型可直接查看的图片扩展名
_IMAGE_EXTS: set[str] = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

_TEXT_MAX_BYTES = 1 * 1024 * 1024  # 文本文件大小上限
_MAX_PX = 2048  # 发送给模型前的最长边上限


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


@tool
def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str | list:
    """读取文件内容。
    - 文本文件：返回带行号的内容，offset 指定起始行（1-based，0=从头），limit 指定最多行数。
    - 图片文件（png/jpg/jpeg/gif/webp/bmp）：直接作为图片内容块传给模型查看。
    - 其他二进制文件：返回错误提示。"""
    scope = get_file_scope()
    if scope is not None:
        allowed, reason = scope.check_access(file_path)
        if not allowed:
            return f"拒绝访问：{reason}"

    path = Path(file_path)

    # Smart path fallback: if the path doesn't exist as given (relative to CWD),
    # try stripping a leading directory component that matches the project/CWD name.
    # This handles the case where the user provides "my_agent/photo.png" but CWD
    # is already "my_agent/" so the correct path is just "photo.png".
    if not path.is_absolute() and not path.exists():
        parts = path.parts
        if len(parts) > 1:
            ref_name = (scope.project_dir.name if scope is not None else Path.cwd().name).lower()
            if parts[0].lower() == ref_name:
                stripped = Path(*parts[1:])
                if stripped.exists():
                    path = stripped
                elif scope is not None and (scope.project_dir / stripped).exists():
                    path = scope.project_dir / stripped

    if not path.exists():
        return f"错误：文件 '{file_path}' 不存在"
    if not path.is_file():
        return f"错误：'{file_path}' 不是文件"

    ext = path.suffix.lower()

    # ── 图片格式 ───────────────────────────────────────────────────────────
    if ext in _IMAGE_EXTS:
        data, media_type = _prepare_image(path.read_bytes(), ext)
        b64 = base64.standard_b64encode(data).decode("ascii")
        return [
            {"type": "text", "text": f"图片文件：{file_path}"},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]

    # ── 文本格式 ───────────────────────────────────────────────────────────
    size = path.stat().st_size
    if size > _TEXT_MAX_BYTES:
        return f"错误：文件 '{file_path}' 超过 1MB 限制（{size} bytes）"

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (
            f"错误：'{file_path}' 是二进制文件，当前不支持此格式。"
            f"支持的格式：文本文件（UTF-8）、图片（png/jpg/jpeg/gif/webp/bmp）。"
        )

    lines = text.splitlines()
    if not lines:
        return ""

    start_idx = max(0, offset - 1) if offset > 0 else 0
    selected = lines[start_idx : start_idx + limit]
    start_line = start_idx + 1

    width = max(len(str(start_line + len(selected) - 1)) if selected else 1, 4)

    return "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(selected, start=start_line))
