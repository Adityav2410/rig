from pydantic import BaseModel

from ..util.logging import get_logger

logger = get_logger()


class LlmApiRates(BaseModel):
    cost_per_m_output_tokens: float | list[tuple[int, float]]
    cost_per_m_input_tokens: float | list[tuple[int, float]]


def cost(llm_rates: LlmApiRates, input_tokens: int, output_tokens: int) -> float:
    def _find_applicable_rate(rates: float | list[tuple[int, float]], token: int) -> float:
        if isinstance(rates, float):
            return rates
        for idx, (_, rate) in enumerate(rates):
            if idx == len(rates) - 1:
                return rate
            if token < rates[idx + 1][0]:
                return rate
        return 0.0

    return (
        _find_applicable_rate(llm_rates.cost_per_m_input_tokens, input_tokens)
        * input_tokens
        / 1_000_000
        + _find_applicable_rate(llm_rates.cost_per_m_output_tokens, output_tokens)
        * output_tokens
        / 1_000_000
    )


_RATES = {
    "claude-haiku-5-5": LlmApiRates(
        cost_per_m_input_tokens=[(0, 0.1), (100_000, 0.5)],
        cost_per_m_output_tokens=[(0, 0.5), (100_000, 2.5)],
    )
}


def price(model: str, usage: dict[str, int]) -> float:
    _api_rates = _RATES.get(model)
    if _api_rates is None:
        logger.error(f"Rate not available for model {model}")
        return 0

    return cost(_api_rates, usage["input_tokens"], usage["output_tokens"])
