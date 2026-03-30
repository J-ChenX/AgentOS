# Contributing to AgentOS

Thank you for your interest in contributing!

## Environment Setup

1. Install [mise](https://mise.jdx.dev/) for toolchain management
2. Clone the repo and run:
   ```bash
   mise install          # installs Python 3.14, Node 24, pnpm
   pip install -e ".[dev]"
   cd web && pnpm install
   ```

## Development Workflow

Start both services in separate terminals:

```bash
# Terminal 1 — Frontend (HMR on port 6493)
cd web && pnpm dev

# Terminal 2 — Backend (hot-reload on port 8000)
agentos run --dev --port 8000
```

Open http://localhost:6493 in your browser.

## Code Standards

**Python** — uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:
```bash
python -m ruff check src/       # lint
python -m ruff format src/      # format
python -m pytest tests/ -v      # tests
```

**TypeScript/CSS** — uses [Prettier](https://prettier.io/):
```bash
cd web
pnpm lint          # ESLint
pnpm format        # Prettier format
pnpm format:check  # Prettier check
```

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add web search skill
fix: handle empty tool_calls from LLM
refactor: simplify skill loader path resolution
docs: update CONTRIBUTING setup steps
chore: upgrade litellm to 1.50.0
```

## Pull Request Process

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes with tests
3. Ensure all checks pass:
   - `python -m pytest tests/ -v`
   - `python -m ruff check src/`
   - `cd web && pnpm lint && pnpm format:check`
4. Open a PR — fill in the PR template

## Issues

Please use the issue templates for bug reports and feature requests. Include reproduction steps and environment details for bugs.
