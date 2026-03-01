from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from aiengine.types import LocalFile, UploadedRef, Provider


class AgentAbstract(ABC):
    provider: Provider

    @abstractmethod
    def upload_files(self, files: List[LocalFile]) -> List[UploadedRef]:
        raise NotImplementedError

    @abstractmethod
    def push_message(
        self,
        *,
        model: str,
        system_prompt: Optional[str],
        payload: Dict[str, Any],
        uploads: Optional[List[UploadedRef]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError