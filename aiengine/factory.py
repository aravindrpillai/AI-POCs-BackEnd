from __future__ import annotations

from aiengine.types import Provider
from aiengine.agents.base import AgentAbstract
from ai.constants import OPENAI_API_KEY, CLAUDE_API_KEY
from aiengine.agents.openai import OpenAIAdapter
from aiengine.agents.claude import ClaudeAdapter
from aiengine.agents.ollama import OllamaAdapter


class AdapterFactory:

    @staticmethod
    def create(provider: Provider) -> AgentAbstract:
        if provider == "openai":
            return OpenAIAdapter(api_key=OPENAI_API_KEY)
        if provider == "claude":
            return ClaudeAdapter(api_key=CLAUDE_API_KEY)
        if provider == "ollama":
            return OllamaAdapter()
        raise ValueError(f"Unsupported provider: {provider}")