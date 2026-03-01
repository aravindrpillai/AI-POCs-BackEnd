from __future__ import annotations

import os, mimetypes, base64
from ollama import Client
from typing import List, Optional, Dict, Any
from aiengine.agents.base import AgentAbstract
from aiengine.types import LocalFile, UploadedRef


class OllamaAdapter(AgentAbstract):
    provider = "ollama"

    def __init__(self, host: Optional[str] = None):
        self.client = Client(host=host or os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    @staticmethod
    def _resolve_filename(f: LocalFile) -> str:
        return f.filename or os.path.basename(f.path)

    @staticmethod
    def _resolve_mime(f: LocalFile) -> str:
        if f.mime_type:
            return f.mime_type
        mt, _ = mimetypes.guess_type(f.path)
        return mt or "application/octet-stream"

    @staticmethod
    def _b64(path: str) -> str:
        return base64.b64encode(open(path, "rb").read()).decode("utf-8")

    def upload_files(self, files: List[LocalFile]) -> List[UploadedRef]:
        """
        Ollama has no files API. Store files as base64 in UploadedRef.file_id
        as a data URI so push_message can use them inline.
        """
        out: List[UploadedRef] = []
        for f in files:
            mt = self._resolve_mime(f)
            b64 = self._b64(f.path)
            # Encode the data URI into file_id — no real upload happens
            data_uri = f"data:{mt};base64,{b64}"
            out.append(UploadedRef(
                provider="ollama",
                file_id=data_uri,  # inline data stored here
                filename=self._resolve_filename(f),
                mime_type=mt,
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

        # Ollama accepts images as a list of base64 strings in the message
        images: List[str] = []
        for u in (uploads or []):
            if u.provider != "ollama":
                continue
            if u.mime_type.startswith("image/"):
                # Strip the data URI prefix, ollama wants raw base64
                b64 = u.file_id.split(",", 1)[-1]
                images.append(b64)
            # Note: Ollama doesn't support PDF/doc attachments natively

        msg: Dict[str, Any] = {"role": "user", "content": payload_text}
        if images:
            msg["images"] = images

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(msg)

        params: Dict[str, Any] = {"model": model, "messages": messages}
        if extra:
            params.update(extra)

        resp = self.client.chat(**params)
        text = resp.get("message", {}).get("content", "") if isinstance(resp, dict) else getattr(resp.message, "content", "")

        return {"text": text.strip(), "raw": resp}