from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class TaskCreate(BaseModel):
    task: str
    agent_id: str | None = None


class TaskCreated(BaseModel):
    task_id: str


class ActionSubmit(BaseModel):
    payload: Any


class SkillToggle(BaseModel):
    enabled: bool


class ConfigPatch(BaseModel):
    project: dict[str, str] | None = None
    llm: dict[str, str] | None = None
    agent: dict[str, str | int] | None = None
    scope: dict[str, list[str]] | None = None


class SkillInfo(BaseModel):
    name: str
    description: str
    enabled: bool
    file: str


class FileNodeModel(BaseModel):
    name: str
    path: str
    is_dir: bool
    children: list[FileNodeModel] | None = None


class AgentConfigModel(BaseModel):
    project: dict[str, str]
    llm: dict[str, str]
    agent: dict[str, Any]
    scope: dict[str, list[str]]


class TaskRecord(BaseModel):
    task_id: str
    created_at: str
    task: str
    status: Literal["running", "done", "error", "cancelled"]
    events: list[dict[str, Any]]
    summary: str | None = None


class AgentStateResponse(BaseModel):
    state: str
    question: dict | None = None


class TurnRecord(BaseModel):
    turn_id: str
    user_message: str
    user_message_hash: str = ""  # SHA-256 of user_message, first 16 hex chars
    created_at: str
    status: Literal["running", "done", "error", "cancelled"]
    events: list[dict[str, Any]] = []
    assistant_message: str | None = None
    annotations: list[Annotation] = []


class SessionRecord(BaseModel):
    session_id: str
    title: str  # first 60 chars of first user_message
    created_at: str
    updated_at: str
    turns: list[TurnRecord] = []


class SessionCreate(BaseModel):
    user_message: str


class TurnCreate(BaseModel):
    user_message: str
    turn_id: str | None = None


class AnnotationType(str, Enum):
    deleted = "deleted"
    emphasized = "emphasized"
    replaced = "replaced"


class Annotation(BaseModel):
    annotation_id: str = ""
    target: Literal["user", "assistant"]
    start: int
    end: int
    original: str
    type: AnnotationType
    replacement: str | None = None


class AnnotationCreate(BaseModel):
    target: Literal["user", "assistant"]
    start: int
    end: int
    original: str
    type: AnnotationType
    replacement: str | None = None


class SessionCreated(BaseModel):
    session_id: str
    turn_id: str


class TurnCreated(BaseModel):
    turn_id: str


# Seal forward reference: TurnRecord.annotations uses Annotation which is defined after TurnRecord.
TurnRecord.model_rebuild()
