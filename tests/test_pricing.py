"""Prices come from pricing/*.json: every model, cache tokens included, tiers by prompt size."""

import pytest

from rig.core.pricing import price, rates


def _usage(
    input_tokens: int = 0, output_tokens: int = 0, read: int = 0, write: int = 0
) -> dict[str, int]:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": read,
        "cache_write_tokens": write,
    }


def test_a_model_other_than_haiku_is_priced() -> None:
    # Sonnet 5.5: $2 in, $10 out per million tokens.
    assert price("claude-sonnet-5-5", _usage(1_000_000, 100_000)) == pytest.approx(2.0 + 1.0)


def test_cache_reads_and_writes_are_charged() -> None:
    # Sonnet 5.5: cache hit $0.10, 5-minute cache write $2.50 per million tokens.
    assert price("claude-sonnet-5-5", _usage(read=1_000_000, write=1_000_000)) == pytest.approx(2.6)


def test_haikus_tier_is_chosen_by_the_whole_prompt() -> None:
    up_to, over = rates("claude-haiku-5-5", 100_000), rates("claude-haiku-5-5", 100_001)
    assert up_to is not None and over is not None
    assert (up_to["input"], over["input"]) == (0.10, 0.50)
    # 60k uncached + 50k read from cache is a 110k prompt: the whole call moves to the higher tier.
    small = price("claude-haiku-5-5", _usage(60_000, 1_000))
    large = price("claude-haiku-5-5", _usage(60_000, 1_000, read=50_000))
    assert small == pytest.approx((60_000 * 0.10 + 1_000 * 0.50) / 1e6)
    assert large == pytest.approx((60_000 * 0.50 + 1_000 * 2.50 + 50_000 * 0.05) / 1e6)


def test_an_unknown_model_costs_nothing_rather_than_failing() -> None:
    assert price("not-a-model", _usage(1_000, 1_000)) == 0.0


def test_openai_and_openrouter_models_are_priced() -> None:
    # GPT-6 Luna: $0.10 in, $0.50 out per million up to 272k prompt tokens, then $0.20 / $0.75.
    assert price("gpt-6-luna", _usage(100_000, 100_000)) == pytest.approx(0.06)
    assert rates("gpt-6-luna", 272_001) == rates("gpt-6-luna", 300_000) != rates("gpt-6-luna", 1)
    assert price("openai/gpt-6-luna", _usage(1_000_000)) == pytest.approx(0.10)
