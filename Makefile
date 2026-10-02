.PHONY: setup dev migrate seed test lint
setup:
	cp -n .env.example .env || true
	docker compose up -d --build
	docker compose exec backend alembic upgrade head
dev:
	docker compose up -d --build
migrate:
	docker compose exec backend alembic upgrade head
seed:
	docker compose exec -e DEV_SEED_PASSWORD backend python -m app.workers.seed
test:
	cd backend && pytest
lint:
	cd backend && ruff check app tests && mypy app
