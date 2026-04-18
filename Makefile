.PHONY: install-frontend install-backend bootstrap backend frontend dev

# Default python and pip (can be overridden by the user)
PYTHON ?= python
PIP ?= pip

# Installation
install-backend:
	cd backend && $(PIP) install -r requirements.txt

install-frontend:
	cd frontend && npm install

# Data Bootstrap
bootstrap:
	$(PYTHON) scripts/bootstrap_sample_data.py

# Running independent servers
backend:
	cd backend && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

# Run both in the same terminal using basic ampersand chaining 
# On pure Windows, running `make dev` might require WSL or Git Bash.
dev:
	@echo "Booting NeuroVynx Local Cluster..."
	make backend & make frontend
