from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class LLMConfig:
    """LLM configuration for agentos agent."""

    model: str = ""
    base_url: str = ""
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.2
    max_tokens: int | None = None

    def resolve_model(self) -> str:
        """base_url 已设置且 model 无显式 provider 前缀时，加 openai/ 强制走 compat 路由。"""
        if self.base_url and "/" not in self.model:
            return f"openai/{self.model}"
        return self.model

    def to_litellm_kwargs(self, *, stream: bool = False) -> dict:
        kwargs: dict = {
            "model": self.resolve_model(),
            "temperature": self.temperature,
            "stream": stream,
        }
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                kwargs["api_key"] = key
        if self.base_url:
            kwargs["api_base"] = self.base_url
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        return kwargs


@dataclass
class ProjectConfig:
    """agent.toml 解析结果"""

    name: str = ""
    version: str = "0.1.0"
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent_type: str = "react"
    max_iterations: int = 20
    system_prompt_path: str = "agent.md"
    memory_path: str = "memory.md"
    skills: dict[str, dict[str, Any]] = field(default_factory=dict)
    scope_allow: list[str] = field(default_factory=lambda: ["./"])
    scope_deny: list[str] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: Path) -> ProjectConfig:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        scope = data.get("scope", {})
        agent = data.get("agent", {})
        llm_section = data.get("llm", {})
        return cls(
            name=data.get("project", {}).get("name", ""),
            version=data.get("project", {}).get("version", "0.1.0"),
            llm=LLMConfig(
                model=llm_section.get("model", ""),
                base_url=llm_section.get("base_url", ""),
                api_key_env=llm_section.get("api_key_env", "OPENAI_API_KEY"),
                temperature=llm_section.get("temperature", 0.2),
                max_tokens=llm_section.get("max_tokens"),
            ),
            agent_type=agent.get("type", "react"),
            max_iterations=agent.get("max_iterations", 20),
            system_prompt_path=agent.get("system_prompt_path", "agent.md"),
            memory_path=agent.get("memory_path", "memory.md"),
            skills=data.get("skills", {}),
            scope_allow=scope.get("allow", ["./"]),
            scope_deny=scope.get("deny", []),
        )
