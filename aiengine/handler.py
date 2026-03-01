from __future__ import annotations

from aiengine.factory import AdapterFactory
from typing import List, Optional, Dict, Any
from aiengine.agents.base import AgentAbstract
from aiengine.types import Provider, LocalFile, UploadedRef


class AIAgentHandler:

    def __init__(self, *, provider: Provider, model: str, system_prompt: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.system_prompt = system_prompt
        self.adapter: AgentAbstract = AdapterFactory.create(provider)

    def upload_files(self, files: List[LocalFile]) -> List[UploadedRef]:
        """Upload once, store the returned refs, reuse across push_message calls."""
        return self.adapter.upload_files(files)

    def push_message(
        self,
        payload: Dict[str, Any],
        uploads: Optional[List[UploadedRef]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.adapter.push_message(
            model=self.model,
            system_prompt=self.system_prompt,
            payload=payload,
            uploads=uploads,
            extra=extra,
        )