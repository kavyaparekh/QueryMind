.PHONY: help up down seed logs psql clean backend

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "QueryMind — available make targets"
	@echo ""
	@echo "  make up       Start Docker services (Postgres + pgvector)"
	@echo "  make seed     Download Chinook data and seed the database"
	@echo "  make down     Stop Docker services"
	@echo "  make clean    Stop services and remove data volumes"
	@echo "  make psql     Open a psql shell in the running container"
	@echo "  make logs     Tail Postgres logs"
	@echo "  make backend  Install Python deps and start the FastAPI server"
	@echo ""

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "Waiting for Postgres to be healthy..."
	@until docker compose exec postgres pg_isready -U $${DB_USER:-querymind} -d $${DB_NAME:-querymind} > /dev/null 2>&1; do \
		printf '.'; sleep 1; \
	done
	@echo " Ready."

down:
	docker compose down

clean:
	docker compose down -v
	@echo "Volumes removed."

logs:
	docker compose logs -f postgres

psql:
	docker compose exec postgres psql -U $${DB_USER:-querymind} -d $${DB_NAME:-querymind}

# ── Seed ──────────────────────────────────────────────────────────────────────
seed: up
	cd db && pip install -q -r requirements.txt && python seed.py

# ── Backend ───────────────────────────────────────────────────────────────────
backend:
	cd backend && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app \
		--reload \
		--host $${BACKEND_HOST:-0.0.0.0} \
		--port $${BACKEND_PORT:-8000}
