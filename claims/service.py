from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from claims.models import ClaimConversation, ClaimMessage


@dataclass(frozen=True)
class ConversationReadModel:
    uid: str
    submitted: bool
    created_at: Any
    state_json: Dict[str, Any]
    summary: Optional[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    text_messages: List[Dict[str, Any]]
    file_messages: List[Dict[str, Any]]


class ClaimConversationStore:
    """
    Storage/service layer for ClaimConversation + ClaimMessage.

    Principles:
    - ClaimConversation.state_json is the single source of truth for the evolving FNOL payload.
    - ClaimMessage stores atomic events (text or file).
    - File is handled separately via add_file_message().
    """

    # -------------------------
    # Conversation lifecycle
    # -------------------------

    @transaction.atomic
    def create_conversation(self, initial_state: Optional[Dict[str, Any]] = None) -> ClaimConversation:
        conv = ClaimConversation.objects.create(
            state_json=initial_state or {},
            state_version=1,
            summary=None,
            submitted=False,
        )
        return conv

    def get_conversation(self, uid: Union[str, UUID]) -> ClaimConversation:
        return ClaimConversation.objects.get(uid=uid)

    # -------------------------
    # Message creation (TEXT)
    # -------------------------

    @transaction.atomic
    def add_text_message(
        self,
        conversation_uid: Union[str, UUID],
        *,
        role: str,
        message: str,
    ) -> ClaimMessage:
        """
        Adds a text message (user or assistant).
        Enforces model.clean() by calling full_clean().
        """
        if role not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")

        conv = ClaimConversation.objects.select_for_update().get(uid=conversation_uid)

        msg = ClaimMessage(
            conversation=conv,
            role=role,
            message=message,
            is_file=False,
            file_id=None,
            filename=None,
            content_type=None,
        )
        msg.full_clean()  # triggers clean()
        msg.save()

        return msg

    # -------------------------
    # Message creation (FILE)
    # -------------------------

    @transaction.atomic
    def add_file_message(
        self,
        conversation_uid: Union[str, UUID],
        *,
        role: str,
        file_id: Union[str, UUID],
        filename: str,
        content_type: str,
        note: str = "",
    ) -> ClaimMessage:
        """
        Adds a file event message.
        'note' is stored in message field as customer note/caption.
        Enforces model.clean() by calling full_clean().
        """
        if role not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")

        conv = ClaimConversation.objects.select_for_update().get(uid=conversation_uid)

        msg = ClaimMessage(
            conversation=conv,
            role=role,
            message=note or "",
            is_file=True,
            file_id=file_id,
            filename=filename,
            content_type=content_type,
        )
        msg.full_clean()  # triggers clean()
        msg.save()

        return msg

    # -------------------------
    # State management
    # -------------------------

    @transaction.atomic
    def update_state(
        self,
        conversation_uid: Union[str, UUID],
        *,
        state_json: Dict[str, Any],
        bump_version: bool = False,
    ) -> ClaimConversation:
        """
        Replaces state_json (single source of truth).
        You can choose to bump version if your state schema evolves.
        """
        conv = ClaimConversation.objects.select_for_update().get(uid=conversation_uid)
        conv.state_json = state_json
        if bump_version:
            conv.state_version = (conv.state_version or 1) + 1
        conv.updated_at = timezone.now()  # if you add updated_at; safe if you don't
        conv.save(update_fields=["state_json", "state_version"])
        return conv

    @transaction.atomic
    def set_summary(
        self,
        conversation_uid: Union[str, UUID],
        *,
        summary: Dict[str, Any],
    ) -> ClaimConversation:
        """
        Sets final summary JSON (does not automatically mark submitted).
        """
        conv = ClaimConversation.objects.select_for_update().get(uid=conversation_uid)
        conv.summary = summary
        conv.save(update_fields=["summary"])
        return conv

    @transaction.atomic
    def mark_submitted(self, conversation_uid: Union[str, UUID], submitted: bool = True) -> ClaimConversation:
        """
        Marks submitted flag (set True only after pushing to ClaimCenter successfully).
        """
        conv = ClaimConversation.objects.select_for_update().get(uid=conversation_uid)
        conv.submitted = submitted
        conv.save(update_fields=["submitted"])
        return conv

    # -------------------------
    # Read APIs
    # -------------------------

    def read_conversation(self, conversation_uid: Union[str, UUID]) -> ConversationReadModel:
        conv = ClaimConversation.objects.get(uid=conversation_uid)

        qs = conv.messages.all().order_by("created_at")

        messages: List[Dict[str, Any]] = []
        text_messages: List[Dict[str, Any]] = []
        file_messages: List[Dict[str, Any]] = []

        for m in qs:
            item = {
                "id": m.id,
                "role": m.role,
                "created_at": m.created_at,
                "is_file": m.is_file,
                "message": m.message or "",
                "file": None,
            }

            if m.is_file:
                item["file"] = {
                    "file_id": str(m.file_id) if m.file_id else None,
                    "filename": m.filename,
                    "content_type": m.content_type,
                    "note": m.message or "",
                }
                file_messages.append(item)
            else:
                text_messages.append(item)

            messages.append(item)

        return ConversationReadModel(
            uid=str(conv.uid),
            submitted=conv.submitted,
            created_at=conv.created_at,
            state_json=conv.state_json or {},
            summary=conv.summary,
            messages=messages,
            text_messages=text_messages,
            file_messages=file_messages,
        )

    def read_messages(
        self,
        conversation_uid: Union[str, UUID],
        *,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns messages list only (optionally limited).
        """
        conv = ClaimConversation.objects.get(uid=conversation_uid)
        qs = conv.messages.all().order_by("created_at")
        if limit:
            qs = qs[:limit]

        out = []
        for m in qs:
            out.append({
                "role": m.role,
                "is_file": m.is_file,
                "message": m.message or "",
                "file_id": str(m.file_id) if m.file_id else None,
                "filename": m.filename,
                "content_type": m.content_type,
                "created_at": m.created_at,
            })
        return out