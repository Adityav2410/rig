from .anthropic import AnthropicProvider
from .types import Provider


def get_provider(name: str, model: str, *, max_tokens: int = 10_000) -> Provider:
    match name:
        case "anthropic":
            return AnthropicProvider(model, max_tokens=max_tokens)
        case _:
            raise ValueError(f"Unknown provider {name!r}. Known providers: anthropic")


__all__ = ["AnthropicProvider", "Provider", "get_provider"]
