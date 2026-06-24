# ── DataFlow Makefile ────────────────────────────────────────────────────────
# NOTE: On Windows, run commands directly in PowerShell instead of using make.
# See SETUP.md for PowerShell instructions.
.PHONY: help backend frontend migrate migrate-down lint type-check clean

help:
	@echo ""
	@echo "  DataFlow — Multi-Agent AI Data Analyst"
	@echo ""
	@echo "  make backend      Start FastAPI dev server on :8000"
	@echo "  make frontend     Start Vite dev server on :5173"
	@echo "  make migrate      Run Alembic migrations (upgrade head)"
	@echo "  make migrate-down Roll back one Alembic migration"
	@echo "  make lint         Run ruff + mypy on backend"
	@echo "  make type-check   Run tsc --noEmit on frontend"
	@echo "  make clean        Remove build artifacts and caches"
	@echo ""

# ── Run ──────────────────────────────────────────────────────────────────────
backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

# ── Database ─────────────────────────────────────────────────────────────────
migrate:
	cd backend && alembic upgrade head

migrate-down:
	cd backend && alembic downgrade -1

# ── Code quality ─────────────────────────────────────────────────────────────
lint:
	cd backend && python -m ruff check . && python -m mypy app --ignore-missing-imports

type-check:
	cd frontend && npm run type-check

# ── Cleanup ──────────────────────────────────────────────────────────────────
clean:
	rm -rf frontend/dist frontend/node_modules
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find backend -name "*.pyc" -delete 2>/dev/null; true
