from fastapi import APIRouter, HTTPException

from agentos.server.models import SkillInfo, SkillToggle

_STUB_SKILLS = [
    SkillInfo(
        name="fetch_image",
        description="下载并预处理图片",
        enabled=True,
        file="skills/fetch_image.py",
    ),
    SkillInfo(
        name="match_template",
        description="多特征融合模板匹配",
        enabled=True,
        file="skills/match_template.py",
    ),
    SkillInfo(
        name="generate_chart",
        description="生成统计图表",
        enabled=True,
        file="skills/generate_chart.py",
    ),
]


def create_skills_router() -> APIRouter:
    router = APIRouter()

    @router.get("/skills")
    async def list_skills():
        return [s.model_dump() for s in _STUB_SKILLS]

    @router.patch("/skills/{name}")
    async def toggle_skill(name: str, body: SkillToggle):
        skill = next((s for s in _STUB_SKILLS if s.name == name), None)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.enabled = body.enabled
        return skill.model_dump()

    return router
