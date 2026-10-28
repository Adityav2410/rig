.PHONY: help lint format fmt-check fix isort typecheck test course

# The local site container serves this directory; set COURSE_DEPLOY_DIR= to skip the copy.
COURSE_DEPLOY_DIR ?= ../rig-study

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

course: ## Rebuild the course site and plan, then copy index.html to the deploy dir
	python3 course/tools/build.py
	python3 course/tools/export.py
	@if [ -n "$(COURSE_DEPLOY_DIR)" ] && [ -d "$(COURSE_DEPLOY_DIR)" ]; then \
		cp course/index.html "$(COURSE_DEPLOY_DIR)/index.html" && \
		echo "copied index.html to $(COURSE_DEPLOY_DIR)"; \
	fi
