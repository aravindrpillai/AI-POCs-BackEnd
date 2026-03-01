from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

Provider = Literal["openai", "claude", "ollama"]

@dataclass(frozen=True)
class LocalFile:
    path: str
    filename: Optional[str] = None
    mime_type: Optional[str] = None

@dataclass(frozen=True)
class UploadedRef:
    provider: Provider
    file_id: str
    filename: str
    mime_type: str