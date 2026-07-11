.PHONY: install dev test lint format typecheck migrate

# Install all Python and Node dependencies
install:
	uv sync --all-packages
	pnpm install

# Run all backend services locally (see compose.yaml for containerized dev)
dev:
	docker compose up --build

test:
	uv run pytest
	pnpm test

lint:
	uv run ruff check .
	uv run ruff format --check .
	pnpm lint

format:
	uv run ruff format .
	pnpm exec prettier --write .

typecheck:
	uv run mypy packages
	@for d in services/*; do echo "mypy $$d"; uv run mypy "$$d" || exit 1; done
	pnpm typecheck

# Apply Alembic migrations for every service that has them (DATABASE_URL from .env)
migrate:
	@for ini in services/*/alembic.ini; do \
		svc=$$(basename $$(dirname "$$ini")); \
		echo "alembic upgrade head [$$svc]"; \
		uv run --package "$$svc" alembic -c "$$ini" upgrade head || exit 1; \
	done
