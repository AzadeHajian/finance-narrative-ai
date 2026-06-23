# llm/__init__.py
from .base import BaseLLM
from .anthropic_client import AnthropicLLM
from .openai_client import OpenAILLM


def get_llm(provider: str = "anthropic", temperature: float = 0.0) -> BaseLLM:
    if provider == "anthropic":
        return AnthropicLLM(temperature=temperature)
    elif provider == "openai":
        return OpenAILLM(temperature=temperature)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'anthropic' or 'openai'")