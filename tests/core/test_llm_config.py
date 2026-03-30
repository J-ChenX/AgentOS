"""Tests for LLMConfig.resolve_model() and to_litellm_kwargs()."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agentos.core.project_config import LLMConfig


class TestResolveModel:
    def test_base_url_set_no_slash_adds_openai_prefix(self):
        cfg = LLMConfig(model="gemini-3-pro-preview", base_url="https://ai.t8star.cn/v1")
        assert cfg.resolve_model() == "openai/gemini-3-pro-preview"

    def test_base_url_set_model_has_slash_unchanged(self):
        cfg = LLMConfig(model="anthropic/claude-3", base_url="https://proxy.example.com/v1")
        assert cfg.resolve_model() == "anthropic/claude-3"

    def test_no_base_url_model_unchanged(self):
        cfg = LLMConfig(model="claude-3-5-sonnet-20241022")
        assert cfg.resolve_model() == "claude-3-5-sonnet-20241022"

    def test_empty_base_url_model_unchanged(self):
        cfg = LLMConfig(model="llama3.2", base_url="")
        assert cfg.resolve_model() == "llama3.2"


class TestToLitellmKwargs:
    def test_stream_false_by_default(self):
        cfg = LLMConfig(model="gpt-4o")
        assert cfg.to_litellm_kwargs()["stream"] is False

    def test_stream_true_when_requested(self):
        cfg = LLMConfig(model="gpt-4o")
        assert cfg.to_litellm_kwargs(stream=True)["stream"] is True

    def test_api_key_injected_when_env_var_set(self):
        cfg = LLMConfig(model="gpt-4o", api_key_env="MY_TEST_KEY_XYZ")
        with patch.dict(os.environ, {"MY_TEST_KEY_XYZ": "sk-test-123"}):
            kwargs = cfg.to_litellm_kwargs()
        assert kwargs["api_key"] == "sk-test-123"

    def test_api_key_absent_when_env_var_missing(self):
        cfg = LLMConfig(model="gpt-4o", api_key_env="MISSING_KEY_XYZ_ABSENT")
        os.environ.pop("MISSING_KEY_XYZ_ABSENT", None)
        assert "api_key" not in cfg.to_litellm_kwargs()

    def test_api_base_injected_when_base_url_set(self):
        cfg = LLMConfig(model="gpt-4o", base_url="https://proxy.example.com/v1")
        assert cfg.to_litellm_kwargs()["api_base"] == "https://proxy.example.com/v1"

    def test_api_base_absent_when_base_url_empty(self):
        cfg = LLMConfig(model="gpt-4o", base_url="")
        assert "api_base" not in cfg.to_litellm_kwargs()

    def test_max_tokens_absent_when_none(self):
        cfg = LLMConfig(model="gpt-4o", max_tokens=None)
        assert "max_tokens" not in cfg.to_litellm_kwargs()

    def test_max_tokens_injected_when_set(self):
        cfg = LLMConfig(model="gpt-4o", max_tokens=4096)
        assert cfg.to_litellm_kwargs()["max_tokens"] == 4096

    def test_temperature_in_kwargs(self):
        cfg = LLMConfig(model="gpt-4o", temperature=0.7)
        assert cfg.to_litellm_kwargs()["temperature"] == 0.7

    def test_model_resolved_with_openai_prefix_when_base_url_set(self):
        cfg = LLMConfig(model="gemini-3-pro-preview", base_url="https://ai.t8star.cn/v1")
        assert cfg.to_litellm_kwargs()["model"] == "openai/gemini-3-pro-preview"
