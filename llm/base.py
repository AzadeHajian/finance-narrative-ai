# llm/base.py
# -----------------------------------------------------------
# Abstract base class that defines the contract all LLM clients
# must follow. Think of it as a blueprint — every provider
# (Anthropic, OpenAI) must implement the same 3 methods.
# This is what allows easy swapping: the rest of the app only
# talks to BaseLLM, never directly to a specific provider.
# -----------------------------------------------------------


# llm/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseLLM(ABC):
    """
    Abstract base class for all LLM providers.
    Both AnthropicLLM and OpenAILLM must implement these methods.
    This means you can swap providers without changing any other code.
    """

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Send a simple prompt, get a string back."""
        pass

    @abstractmethod
    def invoke_with_history(self, messages: List[Dict[str, str]]) -> str:
        """
        Send a conversation history, get a string back.
        messages format: [{"role": "user", "content": "..."}, ...]
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name string e.g. 'claude-sonnet-4-5'"""
        pass