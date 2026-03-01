from __future__ import annotations
from pathlib import Path
from threading import RLock
from typing import Dict

class PromptReader:

    _lock: RLock = RLock()
    _cache: Dict[str, str] = {}

    @classmethod
    def _prompts_dir(cls) -> Path:
         return Path(__file__).resolve().parent

    @classmethod
    def get(cls, filename: str, *, force_reload: bool = False) -> str:
        if not filename or not isinstance(filename, str):
            raise ValueError("Prompt filename must be a non-empty string.")

        # Normalize to avoid duplicate keys like "./x.txt"
        key = filename.strip().replace("\\", "/")

        with cls._lock:
            if not force_reload and key in cls._cache:
                return cls._cache[key]

            prompt_path = cls._prompts_dir() / key
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt not found: {prompt_path}")

            text = prompt_path.read_text(encoding="utf-8").strip()
            if not text:
                raise ValueError(f"Prompt file is empty: {prompt_path}")

            cls._cache[key] = text
            return text

    @classmethod
    def clear_cache(cls) -> None:
        with cls._lock:
            cls._cache.clear()
