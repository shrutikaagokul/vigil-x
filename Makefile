.PHONY: help install data pipeline db run test test-backend clean all frontend-build

PYTHON ?= python
UVICORN ?= uvicorn

help:
	@echo "Vigil-X / ClaimShield Nexus — Command Interface"
	@echo "==============================================="
	@echo "make all           Full reproducible build: pipeline + db + test + frontend"
	@echo "make install       Install backend and analytical dependencies"
	@echo "make data          Generate synthetic claims dataset"
	@echo "make pipeline      Run detection rules (R01-R10), network, risk engine, and build db"
	@echo "make db            Build/rebuild SQLite application database (app.db)"
	@echo "make run           Launch FastAPI investigation backend server"
	@echo "make test          Run full test suite (rules + backend + investigation)"
	@echo "make test-backend  Run backend API, database, and verifier tests"
	@echo "make frontend-build Build the React frontend"
	@echo "make validate      Run endpoint validation script"
	@echo "make clean         Remove cache and temporary test databases"

install:
	pip install -r requirements.txt
	npm install

data:
	$(PYTHON) -c "from generator.synthetic_data import generate_synthetic_data; generate_synthetic_data(n_providers=150, n_members=3000, n_facilities=25, n_months=12, output_dir='data')"

pipeline:
	$(PYTHON) scripts/build_db.py

db:
	$(PYTHON) scripts/build_db.py --quick

run:
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -v

test-backend:
	pytest -v tests/test_backend.py tests/test_investigation.py tests/test_contracts.py

frontend-build:
	npm run build

validate:
	$(PYTHON) scripts/validate_endpoints.py

all: install db test frontend-build validate
	@echo ""
	@echo "============================================"
	@echo "  VIGIL-X: FULL BUILD COMPLETED SUCCESSFULLY"
	@echo "============================================"
	@echo "  Backend:  make run"
	@echo "  Frontend: npm run dev"
	@echo "============================================"

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info test_*.db app.db .coverage dist/
