#!/usr/bin/env bash
# Lint and format the repo's Python tooling: tools/*.py and serve.py.
# Config lives in pyproject.toml ([tool.ruff]). content/*.md is intentionally
# excluded — it's a custom markdown dialect, not CommonMark (see GUIDELINES.md
# §1); a generic formatter would corrupt it.
#
#   tools/lint.sh          # check only; exits nonzero if anything needs attention
#   tools/lint.sh --fix    # apply lint autofixes and reformat in place
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uvx >/dev/null 2>&1; then
  RUFF=(uvx ruff)
elif command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
else
  echo "error: need 'uvx' (https://docs.astral.sh/uv/) or 'ruff' (pip install ruff) on PATH" >&2
  exit 1
fi

if [[ "${1:-}" == "--fix" ]]; then
  "${RUFF[@]}" check --fix .
  "${RUFF[@]}" format .
else
  "${RUFF[@]}" check .
  "${RUFF[@]}" format --check .
fi
