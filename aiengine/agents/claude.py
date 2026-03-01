from __future__ import annotations

import os, mimetypes, anthropic
from ai.constants import MAX_TOKEN
from typing import List, Optional, Dict, Any
from aiengine.agents.base import AgentAbstract
from aiengine.types import LocalFile, UploadedRef


class ClaudeAdapter(AgentAbstract):
    provider = "claude"

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    @staticmethod
    def _resolve_filename(f: LocalFile) -> str:
        return f.filename or os.path.basename(f.path)

    @staticmethod
    def _resolve_mime(f: LocalFile) -> str:
        if f.mime_type:
            return f.mime_type
        mt, _ = mimetypes.guess_type(f.path)
        return mt or "application/octet-stream"

    def upload_files(self, files: List[LocalFile]) -> List[UploadedRef]:
        out: List[UploadedRef] = []
        for f in files:
            res = self.client.beta.files.upload(
                file=(self._resolve_filename(f), open(f.path, "rb"), self._resolve_mime(f)),
            )
            out.append(UploadedRef(
                provider="claude",
                file_id=res.id,
                filename=self._resolve_filename(f),
                mime_type=self._resolve_mime(f),
            ))
        return out

    def push_message(
        self,
        *,
        model: str,
        system_prompt: Optional[str],
        payload: Dict[str, Any],
        uploads: Optional[List[UploadedRef]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        payload_text = payload if isinstance(payload, str) else str(payload)
        blocks: List[Dict[str, Any]] = [{"type": "text", "text": payload_text}]

        for u in (uploads or []):
            if u.provider != "claude":
                continue
            if u.mime_type.startswith("image/"):
                blocks.append({
                    "type": "image",
                    "source": {"type": "file", "file_id": u.file_id},
                })
            else:
                blocks.append({
                    "type": "document",
                    "source": {"type": "file", "file_id": u.file_id},
                    "title": u.filename,
                })

        params: Dict[str, Any] = {
            "model": model,
            "max_tokens": MAX_TOKEN,
            "messages": [{"role": "user", "content": blocks}],
            "betas": ["files-api-2025-04-14"],  # required header for files API
        }
        if system_prompt:
            params["system"] = system_prompt
        if extra:
            params.update(extra)

        resp = self.client.beta.messages.create(**params)

        text_parts: List[str] = []
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))

        return {"text": "\n".join(text_parts).strip(), "raw": resp}