from __future__ import annotations
from datetime import date
import uuid, traceback
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from claims.prompts.reader import PromptReader
from claims.services import ClaimService
from claims.utils import get_handler, resolve_uploads, log_claude_response, parse_ai_response


class ClaimsAPIView(APIView):
    parser_classes = [JSONParser]

    def get(self, request, conv_id: uuid.UUID = None):
        if not conv_id:
            return Response(
                {"error": "conv_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        conv = ClaimService.get_conversation(conv_id)
        if not conv:
            return Response(
                {"error": "conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        messages = [
            {
                "role":         m.role,
                "message":      m.message,
                "is_file":      m.is_file,
                "filename":     m.filename if m.is_file else None,
                "content_type": m.content_type if m.is_file else None,
                "created_at":   m.created_at.isoformat(),
            }
            for m in conv.messages.order_by("created_at")
        ]

        return Response({
            "conv_id":   str(conv.uid),
            "submitted": conv.submitted,
            "summary":   conv.summary,
            "messages":  messages,
        }, status=status.HTTP_200_OK)

    def post(self, request, conv_id: uuid.UUID = None):
        try:
            msg = (request.data.get("msg") or "").strip()

            company      = request.GET.get("company")
            email        = request.GET.get("email")
            name         = request.GET.get("name")
            policynumber = request.GET.get("policynumber")
            mobile       = request.GET.get("mobile")

            # Only use them if company is present (mirrors frontend logic)
            user_info = ''
            if company:
                user_info = f"My name is {name}, policynumber is {policynumber}, contact number is {mobile} and email is {email}"
             
            # ── Init: create conversation and return conv_id ───────────────
            if not msg or msg == "__init__":
                conv = ClaimService.create_conversation()
                return Response(
                    {"conv_id": str(conv.uid)},
                    status=status.HTTP_200_OK
                )
            
            prompt = PromptReader.get("claimsprompt.txt", variables={"__today__": date.today().isoformat(), "__user_info__" : user_info})
            
            # ── 1. Get or create conversation ──────────────────────────────
            if conv_id:
                conv = ClaimService.get_conversation(conv_id)
                if not conv:
                    return Response(
                        {"error": "conversation not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                if conv.submitted:
                    return Response(
                        {"error": "conversation already submitted"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                conv = ClaimService.create_conversation()

            # ── 2. Save user message ───────────────────────────────────────
            ClaimService.save_user_message(conv, msg)

            # ── 3. Build history + resolve uploads ─────────────────────────
            history       = ClaimService.get_conversation_history(conv)
            file_messages = ClaimService.get_conversation_files(conv)

            handler = get_handler(prompt)
            uploads = resolve_uploads(handler, file_messages)

            # ── 4. Call AI ─────────────────────────────────────────────────
            resp = handler.push_message(
                payload={
                    "conversation":  history,
                    "current_state": conv.state_json,
                    "instruction": (
                        "CRITICAL: Your response MUST be valid JSON only. "
                        "No plain text. No markdown. No code fences. "
                        "Follow the exact output format in your system prompt."
                    ),
                },
                uploads=uploads if uploads else None,
            )

            # ── 5. Log Claude internals ────────────────────────────────────
            log_claude_response(resp)

            raw = resp["text"]
            print(f"[Claude] raw length={len(raw)} preview={raw[:300]}")

            # ── 6. Parse AI response ───────────────────────────────────────
            try:
                ai_response = parse_ai_response(raw)
            except ValueError as e:
                print(f"[Claude] FULL RAW:\n{raw}")
                return Response(
                    {"error": str(e), "raw": raw},
                    status=status.HTTP_502_BAD_GATEWAY
                )

            is_summary = ai_response.get("summary") == "true"
            ai_msg = (
                "Your FNOL is complete."
                if is_summary
                else ai_response.get("message", "")
            )

            # ── 7. Save reply + update state ───────────────────────────────
            ClaimService.save_assistant_message(conv, ai_msg)
            ClaimService.update_state(conv, ai_response)

            # ── 8. Return ──────────────────────────────────────────────────
            return Response({
                "conv_id": str(conv.uid),
                "reply":   ai_msg,
                "summary": is_summary,
                "data":    conv.summary if is_summary else None,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("===ERROR:\n", traceback.format_exc())
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )