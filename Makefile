.PHONY: build-web build-py build dev clean install-dev

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
