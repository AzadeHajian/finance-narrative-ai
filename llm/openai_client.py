# llm/openai_client.py
# -----------------------------------------------------------
# GPT-4o implementation of BaseLLM using langchain-openai.
# Reads OPENAI_API_KEY from .env and wraps GPT-4o.
# Identical interface to AnthropicLLM — swap by changing
# the provider string in get_llm(), nothing else changes.
# -----------------------------------------------------------

import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from llm.base import BaseLLM

load_dotenv()


class OpenAILLM(BaseLLM):
    """
    GPT-4o via langchain-openai.
    Reads OPENAI_API_KEY from .env
    """

    def __init__(self, model: str = "gpt-4o-2024-11-20", temperature: float = 0.0):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")

        self.model_name = model
        self.temperature = temperature
        self.client = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=temperature,  # 0 = deterministic, faithful drafts
            max_tokens=2048,
        )

    def invoke(self, prompt: str) -> str:
        """Single prompt → single response."""
        try:
            messages = [HumanMessage(content=prompt)]
            response = self.client.invoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"OpenAI invoke failed: {e}") from e

    def invoke_with_history(self, messages: List[Dict[str, str]]) -> str:
        """Multi-turn chat with full message history."""
        try:
            lc_messages = []
            for m in messages:
                role = m.get("role")
                content = m.get("content", "")
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    raise ValueError(f"Unknown message role: '{role}'")

            response = self.client.invoke(lc_messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"OpenAI invoke_with_history failed: {e}") from e

    def get_model_name(self) -> str:
        return self.model_name