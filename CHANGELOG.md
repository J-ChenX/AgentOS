# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CLI: `agentos init`, `agentos run`, `agentos skill` commands
- Web UI: Blender-style tiling window manager with viewport split/merge
- Skills system: builtin, local, and Git-sourced skills with versioned cache
- LLM layer: LiteLLM routing with OpenAI protocol standard
- Agent Runner: Custom ReAct loop with parallel tool execution via asyncio.gather
- Custom `@tool` decorator with Pydantic-powered JSON Schema generation and runtime validation
- Tailwind CSS v4 with CSS-first configuration
- FileScope access control for sandboxed skill execution
