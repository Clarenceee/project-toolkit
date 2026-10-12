.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= 3.11
SOURCES := reusable_helpers scripts examples tests

.PHONY: help setup lock format format-check lint typecheck security test check

help:
	@echo "setup         Install runtime dependencies and development tools"
	@echo "lock          Resolve and update uv.lock"
	@echo "format        Fix lint issues and format Python files"
	@echo "check         Run formatting, lint, type, security, and test checks"
	@echo "Individual checks: format-check lint typecheck security test"

setup:
	$(UV) sync --all-extras --python $(PYTHON)

lock:
	$(UV) lock --python $(PYTHON)

format:
	$(UV) run --all-extras ruff check --fix $(SOURCES)
	$(UV) run --all-extras black $(SOURCES)

format-check:
	$(UV) run --all-extras black --check $(SOURCES)

lint:
	$(UV) run --all-extras ruff check $(SOURCES)

typecheck:
	$(UV) run --all-extras mypy

security:
	$(UV) run --all-extras bandit -c pyproject.toml -r reusable_helpers scripts examples

test:
	$(UV) run --all-extras python -m unittest discover -s tests -v

check: format-check lint typecheck security test
