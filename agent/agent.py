import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import List, Dict
from dotenv import load_dotenv

from llm import get_llm
from mcp_server.client import agent_instance

load_dotenv()


class SQLAgent:
    """
    Thin wrapper around the async agent_instance.
    Keeps a synchronous .run() interface for the Streamlit UI.
    """

    def __init__(self, provider: str = "anthropic", temperature: float = 0.0):
        self.provider = provider
        self.temperature = temperature
        self.llm = get_llm(provider, temperature)
        self.model_name = self.llm.get_model_name()

    def run(self, user_message: str, chat_history: List[Dict] = []) -> str:
        return asyncio.run(
            agent_instance(
                user_prompt=user_message,
                provider=self.provider,
                chat_history=chat_history,
                temperature=self.temperature,
            )
        )

    def get_model_name(self) -> str:
        return self.model_name

    def get_provider(self) -> str:
        return self.provider
