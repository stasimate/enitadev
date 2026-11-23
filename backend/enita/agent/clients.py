"""LLM client factory. The provider comes from the settings, never from the code (RF-30)."""

from datapizza.core.clients import Client

from enita.settings import Settings, get_settings


class ProviderConfigError(RuntimeError):
    """The configuration of the LLM provider is not complete."""


def _key(value, name: str) -> str:
    if value is None or not value.get_secret_value():
        raise ProviderConfigError(f"{name} is not set. Add it to the .env file.")
    return value.get_secret_value()


def get_client(settings: Settings | None = None, model: str | None = None) -> Client:
    s = settings or get_settings()
    if model:
        s = s.model_copy(update={"model": model})
    match s.provider:
        case "openai":
            from datapizza.clients.openai import OpenAIClient

            return OpenAIClient(api_key=_key(s.openai_api_key, "OPENAI_API_KEY"), model=s.model)
        case "google":
            from datapizza.clients.google import GoogleClient

            return GoogleClient(api_key=_key(s.google_api_key, "GOOGLE_API_KEY"), model=s.model)
        case "anthropic":
            from datapizza.clients.anthropic import AnthropicClient

            return AnthropicClient(
                api_key=_key(s.anthropic_api_key, "ANTHROPIC_API_KEY"), model=s.model
            )
        case "ollama":
            from datapizza.clients.openai_like import OpenAILikeClient

            return OpenAILikeClient(api_key="ollama", model=s.model, base_url=s.ollama_base_url)
    raise ProviderConfigError(f"Unknown provider: {s.provider}")
