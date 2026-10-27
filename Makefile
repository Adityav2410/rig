.PHONY: help lint format fmt-check fix isort typecheck test

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-12s %s\n", $$1, $$2}'

lint: ## Check code for lint errors
	uv run ruff check .

format: ## Format all files
	uv run ruff format .

fmt-check: ## Check formatting without making changes
	uv run ruff format --check .

fix: ## Auto-fix lint errors and format all files
	uv run ruff check --fix .
	uv run ruff format .

isort: ## Fix import ordering only
	uv run ruff check --fix --select I .

typecheck: ## Run mypy type checking
	uv run mypy rig/

test: ## Run rig's own test suite (not the evals harness)
	uv run pytest -q
