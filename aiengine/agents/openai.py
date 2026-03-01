from __future__ import annotations

import os, mimetypes
from openai import OpenAI
from typing import List, Optional, Dict, Any
from aiengine.agents.base import AgentAbstract
from aiengine.types import LocalFile, UploadedRef


class OpenAIAdapter(AgentAbstract):
    provider = "openai"

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)

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
            res = self.client.files.create(
                file=open(f.path, "rb"),
                purpose="vision",  # use "assistants" for PDFs/docs
            )
            out.append(UploadedRef(
                provider="openai",
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
        content_blocks: List[Dict[str, Any]] = [{"type": "input_text", "text": payload_text}]

        for u in (uploads or []):
            if u.provider != "openai":
                continue
            if u.mime_type.startswith("image/"):
                content_blocks.append({"type": "input_image", "file_id": u.file_id})
            else:
                content_blocks.append({"type": "input_file", "file_id": u.file_id})

        input_msgs: List[Dict[str, Any]] = []
        if system_prompt:
            input_msgs.append({"role": "system", "content": system_prompt})
        input_msgs.append({"role": "user", "content": content_blocks})

        params: Dict[str, Any] = {"model": model, "input": input_msgs}
        if extra:
            params.update(extra)

        resp = self.client.responses.create(**params)
        return {"text": getattr(resp, "output_text", None) or "", "raw": resp}