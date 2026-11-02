"""The dollar cost of one model call, from price tables in dollars per million tokens.

Each *.json file in this package is one vendor's table, keyed by model id: claude.json holds
Anthropic's prices; openai.json holds OpenAI's, plus OpenRouter's ids for the same models
("openai/gpt-6-luna"), which OpenRouter bills at the vendor's rate. OpenAI charges nothing
extra to write its cache, so there cache_write_5m equals input.
A model can be priced in tiers by prompt size ("up_to_100k" / "over_100k"); the tier is chosen
by the whole prompt and then applies to the whole call, input and output alike.
"""

import json
from functools import cache
from pathlib import Path
from typing import Any

from ...util.logging import get_logger

logger = get_logger()

PRICES_DIR = Path(__file__).parent
_unpriced: set[str] = set()


@cache
def _table() -> dict[str, Any]:
    data: dict[str, Any] = {}
    for path in sorted(PRICES_DIR.glob("*.json")):
        data |= json.loads(path.read_text())
    return data


def rates(model: str, prompt_tokens: int) -> dict[str, float] | None:
    """The per-million-token rates for one call, or None for a model not in the table."""
    entry = _table().get(model)
    if entry is None or "input" in entry:
        return entry
    for key, tier in entry.items():  # e.g. "up_to_100k", "over_100k"
        kind, _, size = key.rpartition("_")
        limit = int(size.removesuffix("k")) * 1000
        if (kind == "up_to" and prompt_tokens <= limit) or (
            kind == "over" and prompt_tokens > limit
        ):
            return dict(tier)
    return None


def price(model: str, usage: dict[str, int]) -> float:
    """Dollars for one call, from rig's normalized usage (input excludes cache reads and writes)."""
    cache_read = usage.get("cache_read_tokens", 0)
    cache_write = usage.get("cache_write_tokens", 0)
    prompt = usage["input_tokens"] + cache_read + cache_write
    r = rates(model, prompt)
    if r is None:
        if model not in _unpriced:  # once per model, not once per call
            _unpriced.add(model)
            logger.warning(f"no price for model {model!r}; its calls count as $0 toward the budget")
        return 0.0
    # Cache writes at the 5-minute rate: usage doesn't split writes by TTL yet (Week 3 does).
    return (
        usage["input_tokens"] * r["input"]
        + usage["output_tokens"] * r["output"]
        + cache_read * r["cache_hit"]
        + cache_write * r["cache_write_5m"]
    ) / 1_000_000
