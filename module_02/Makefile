VENV        = .venv
PYTHON      = $(VENV)/bin/python
PIP         = $(VENV)/bin/pip
INPUT       ?= examples/brazil27.toml
GENERATIONS ?=

GENERATIONS_ARG = $(if $(GENERATIONS),--generations $(GENERATIONS),)

.PHONY: setup qa test plan analysis
.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  setup     Create venv, install dependencies, and initialize .env"
	@echo "  qa        Format, lint and typecheck"
	@echo "  test      Run tests with coverage"
	@echo "  plan      Run the VRP planner"
	@echo "            Default:  make plan INPUT=examples/brazil27.toml"
	@echo "            With cap: make plan INPUT=examples/brazil27.toml GENERATIONS=500"
	@echo "  analysis  Start the VRP analysis chatbot"

setup:
	python3.11 -m venv $(VENV)
	chmod +x $(VENV)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📋 Created .env from .env.example — paste your OPENAI_API_KEY in .env before running make analysis"; \
	else \
		echo "✅ .env already exists, skipping"; \
	fi
	@echo "✅ Environment ready. Activate with: source $(VENV)/bin/activate"

qa:
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check . --fix --select E,F,I
	$(VENV)/bin/mypy main.py app.py src/ tests/

test:
	$(VENV)/bin/coverage run --branch --source=src -m unittest discover -s tests -v
	$(VENV)/bin/coverage report -m

plan:
	$(PYTHON) main.py plan --input $(INPUT) $(GENERATIONS_ARG)

analysis:
	$(VENV)/bin/streamlit run app.py
