.PHONY: build-web build-py build dev clean install-dev check check-py check-web

install-dev:
	pip install -e ".[dev]"
	pnpm install

build-web:
	pnpm install
	pnpm --filter web build
	mkdir -p src/agentos/_web_assets
	rm -rf src/agentos/_web_assets/*
	cp -r web/dist/* src/agentos/_web_assets/

build-py: build-web
	python -m build

build: build-py

dev:
	@echo "启动开发环境（在仓库根目录执行）："
	@echo "  pnpm dev                               (前端 HMR + 后端，port 6493)"
	@echo "  浏览器访问: http://localhost:6493"

clean:
	rm -rf src/agentos/_web_assets/*
	rm -rf web/dist
	rm -rf dist/

# ── 本地 CI 检查（提交前运行） ─────────────────────────────────────────────────
check: check-py check-web
	@echo "✓ 全部检查通过"

check-py:
	@echo "==> ruff format check"
	python -m ruff format src/ tests/ --check
	@echo "==> ruff lint"
	python -m ruff check src/ tests/
	@echo "==> pytest"
	python -m pytest tests/ -q

check-web:
	@echo "==> prettier format check"
	pnpm --filter web format:check
	@echo "==> eslint"
	pnpm --filter web lint
	@echo "==> vitest"
	pnpm --filter web exec vitest run
