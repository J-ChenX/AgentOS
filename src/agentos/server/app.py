from __future__ import annotations

import warnings
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agentos.server.routes.actions import create_actions_router
from agentos.server.routes.config import create_config_router
from agentos.server.routes.files import create_files_router
from agentos.server.routes.sessions import create_sessions_router
from agentos.server.routes.skills import create_skills_router
from agentos.server.stub_engine import StubEngine

WEB_ASSETS_DIR = Path(__file__).parent.parent / "_web_assets"


def create_app(dev_mode: bool = False, history_dir: Path | None = None) -> FastAPI:
    # ── Engine factory: reads agent/agent.toml from CWD ───────────────────
    project_dir = Path.cwd()
    agent_toml = project_dir / "agent" / "agent.toml"

    engine: object  # AgentRunner | StubEngine

    if agent_toml.exists():
        try:
            from agentos.core.file_scope import FileScope
            from agentos.core.project_config import ProjectConfig
            from agentos.core.runner import AgentRunner
            from agentos.core.skill_loader import SkillLoader

            config = ProjectConfig.from_toml(agent_toml)
            agent_dir = project_dir / "agent"

            try:
                loaded_skills = SkillLoader(project_dir, config).load_project_skills()
                tools: list = [ts for skill in loaded_skills for ts in skill.tool_functions]
            except Exception as skill_err:
                warnings.warn(
                    f"[AgentOS] SkillLoader 加载失败，以空工具列表启动: {skill_err}", stacklevel=2
                )
                tools = []

            file_scope = FileScope(project_dir, config.scope_allow, config.scope_deny)

            engine = AgentRunner(
                llm_config=config.llm,
                tools=tools,
                file_scope=file_scope,
                max_iterations=config.max_iterations,
                agent_dir=agent_dir,
                system_prompt_path=config.system_prompt_path,
                memory_path=config.memory_path,
                skills_config=config.skills,
            )
        except Exception as e:
            warnings.warn(
                f"[AgentOS] AgentRunner 初始化失败，降级到 StubEngine: {e}", stacklevel=2
            )
            engine = StubEngine()
    else:
        engine = StubEngine()
    # ───────────────────────────────────────────────────────────────────────

    # ── History store ──────────────────────────────────────────────────────
    resolved_history_dir = history_dir or (project_dir / ".agentos" / "history")
    from agentos.core.history_store import HistoryStore

    store = HistoryStore(resolved_history_dir)
    # ───────────────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.startup_sanitization()
        yield

    app = FastAPI(title="AgentOS API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.engine = engine
    app.state.store = store

    app.include_router(create_sessions_router(engine, store), prefix="/api")
    app.include_router(create_actions_router(engine), prefix="/api")
    app.include_router(create_skills_router(), prefix="/api")
    app.include_router(create_files_router(), prefix="/api")
    app.include_router(create_config_router(), prefix="/api")

    @app.get("/api/agent/state")
    async def get_agent_state():
        from agentos.server.models import AgentStateResponse

        engine = app.state.engine
        state = getattr(engine, "state", "idle")
        question = getattr(engine, "pending_question", None)
        return AgentStateResponse(state=state, question=question)

    if not dev_mode and WEB_ASSETS_DIR.exists() and any(WEB_ASSETS_DIR.iterdir()):
        app.mount("/", StaticFiles(directory=WEB_ASSETS_DIR, html=True), name="web")

    return app


app = create_app()
