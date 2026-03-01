from __future__ import annotations

import os, uuid
from django.conf import settings
from claims.models import ClaimConversation, ClaimMessage


class ClaimService:

    @staticmethod
    def create_conversation() -> ClaimConversation:
        return ClaimConversation.objects.create(
            state_json={}, state_version=1, summary=None, submitted=False,
        )

    @staticmethod
    def get_conversation(conv_id) -> ClaimConversation | None:
        try:
            return ClaimConversation.objects.get(uid=conv_id)
        except ClaimConversation.DoesNotExist:
            return None

    @staticmethod
    def save_user_message(conv: ClaimConversation, msg: str) -> ClaimMessage:
        return ClaimMessage.objects.create(
            conversation=conv, role="user", message=msg, is_file=False,
        )

    @staticmethod
    def save_assistant_message(conv: ClaimConversation, msg: str) -> ClaimMessage:
        return ClaimMessage.objects.create(
            conversation=conv, role="assistant", message=msg, is_file=False,
        )

    @staticmethod
    def save_file_message(
        conv: ClaimConversation,
        *,
        file_id: uuid.UUID,
        filename: str,
        content_type: str,
        message: str | None = None,
        provider_file_id: str | None = None,
    ) -> ClaimMessage:
        return ClaimMessage.objects.create(
            conversation=conv,
            role="user",
            is_file=True,
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            message=message,               # optional caption/note from user
            provider_file_id=provider_file_id,
        )

    @staticmethod
    def update_provider_file_id(file_uuid: uuid.UUID, provider_file_id: str) -> None:
        ClaimMessage.objects.filter(file_id=file_uuid, is_file=True).update(
            provider_file_id=provider_file_id
        )

    @staticmethod
    def get_file_message(file_uuid: uuid.UUID) -> ClaimMessage | None:
        try:
            return ClaimMessage.objects.get(file_id=file_uuid, is_file=True)
        except ClaimMessage.DoesNotExist:
            return None

    @staticmethod
    def get_conversation_files(conv: ClaimConversation) -> list[ClaimMessage]:
        return list(conv.messages.filter(is_file=True).order_by("created_at"))

    @staticmethod
    def get_conversation_history(conv: ClaimConversation) -> list[dict]:
        history = []
        for m in conv.messages.order_by("created_at"):
            if m.is_file:
                # Include file as a note in history so AI knows about it
                history.append({
                    "role": "user",
                    "content": f"[File uploaded: {m.filename}]{(' — ' + m.message) if m.message else ''}",
                })
            else:
                history.append({"role": m.role, "content": m.message})
        return history

    @staticmethod
    def update_state(conv: ClaimConversation, ai_response: dict) -> ClaimConversation:
        is_summary = ai_response.get("summary") == "true"
        conv.state_json = ai_response
        conv.state_version += 1
        if is_summary:
            conv.summary = ai_response.get("data", {})
            conv.submitted = True
        conv.save(update_fields=["state_json", "state_version", "summary", "submitted"])
        return conv