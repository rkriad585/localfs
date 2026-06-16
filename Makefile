.PHONY: build run clean test lint format install release docker docker-run help

PROJECT   := localfs
PYTHON    := python3
PIP       := pip3

build:
	$(PYTHON) -m build --wheel --sdist .

run:
	$(PYTHON) main.py

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .ruff_cache
	find . \( -name __pycache__ -o -name '*.pyc' \) -exec rm -rf {} + 2>/dev/null || true

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

install:
	$(PIP) install --user -e .

release: build
	@echo "Release artifacts in dist/"

docker:
	docker build -t $(PROJECT) .

docker-run:
	docker compose up

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build       Build wheel and sdist"
	@echo "  run         Start localfs server"
	@echo "  clean       Remove build artifacts"
	@echo "  test        Run test suite"
	@echo "  lint        Run ruff linter"
	@echo "  format      Run ruff formatter"
	@echo "  install     Install package in editable mode"
	@echo "  release     Build release artifacts"
	@echo "  docker      Build Docker image"
	@echo "  docker-run  Run via docker compose"
