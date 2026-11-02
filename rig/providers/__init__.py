from .anthropic import AnthropicProvider
from .openai_chat import OPENROUTER_URL, OpenAIChatProvider
from .types import Provider

# The model each provider uses when none is given, so switching needs only --provider.
# OpenRouter defaults to the same Haiku as Anthropic: then a difference in results comes from the
# adapter, not the model.
DEFAULT_MODELS = {
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-6-luna",
    "openrouter": "anthropic/claude-haiku-5.5",
}


def get_provider(
    name: str, model: str | None = None, *, max_tokens: int = 10_000, base_url: str | None = None
) -> Provider:
    """A provider by name; `base_url` points it at another server (e.g. Ollama, for openai)."""
    if name not in DEFAULT_MODELS:
        raise ValueError(f"Unknown provider {name!r}. Known providers: {', '.join(DEFAULT_MODELS)}")
    model = model or DEFAULT_MODELS[name]
    match name:
        case "anthropic":
            return AnthropicProvider(model, max_tokens=max_tokens, base_url=base_url)
        case "openai":
            # Any other server speaks only max_tokens; OpenAI itself wants the newer name.
            field = "max_tokens" if base_url else "max_completion_tokens"
            return OpenAIChatProvider(
                model, max_tokens=max_tokens, base_url=base_url, max_tokens_field=field
            )
        case _:  # openrouter
            return OpenAIChatProvider(
                model,
                max_tokens=max_tokens,
                base_url=base_url or OPENROUTER_URL,
                api_key_env="OPENROUTER_API_KEY",
                name="openrouter",
                max_tokens_field="max_tokens",
            )


__all__ = ["DEFAULT_MODELS", "AnthropicProvider", "OpenAIChatProvider", "Provider", "get_provider"]
