import uuid, json, os, traceback
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from claims.prompts.reader import PromptReader
from claims.services import ClaimService
from aiengine import AIAgentHandler, LocalFile, UploadedRef


PROVIDER = "claude"
MODEL    = "claude-sonnet-4-6"
TMP_DIR  = os.path.join(settings.BASE_DIR, "tmp")


def _get_handler(prompt):
    return AIAgentHandler(provider=PROVIDER, model=MODEL, system_prompt=prompt)


def _resolve_uploads(handler, file_messages: list) -> list[UploadedRef]:
    uploads = []
    for fm in file_messages:
        if fm.provider_file_id:
            uploads.append(UploadedRef(
                provider=PROVIDER,
                file_id=fm.provider_file_id,
                filename=fm.filename,
                mime_type=fm.content_type,
            ))
        else:
            local_path = os.path.join(TMP_DIR, str(fm.file_id))
            if not os.path.exists(local_path):
                continue
            refs = handler.upload_files([LocalFile(local_path, filename=fm.filename, mime_type=fm.content_type)])
            if refs:
                ClaimService.update_provider_file_id(fm.file_id, refs[0].file_id)
                uploads.append(refs[0])
    return uploads


class ClaimsAPIView(APIView):
    parser_classes = [JSONParser]

    def get(self, request, conv_id: uuid.UUID = None):
        """Load conversation history + status for reload."""
        if not conv_id:
            return Response({"error": "conv_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        conv = ClaimService.get_conversation(conv_id)
        if not conv:
            return Response({"error": "conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        messages = [
            {
                "role": m.role,
                "message": m.message,
                "is_file": m.is_file,
                "filename": m.filename if m.is_file else None,
                "content_type": m.content_type if m.is_file else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in conv.messages.order_by("created_at")
        ]

        return Response({
            "conv_id": str(conv.uid),
            "submitted": conv.submitted,
            "summary": conv.summary,
            "messages": messages,
        }, status=status.HTTP_200_OK)

    def post(self, request, conv_id: uuid.UUID = None):
        try:
            msg = (request.data.get("msg") or "").strip()

            # Init — just create conversation
            if not msg or msg == "__init__":
                conv = ClaimService.create_conversation()
                return Response({"conv_id": str(conv.uid)}, status=status.HTTP_200_OK)

            prompt = PromptReader.get("claimsprompt.txt")

            # ── 1. Get or create conversation ──────────────────────────────
            if conv_id:
                conv = ClaimService.get_conversation(conv_id)
                if not conv:
                    return Response({"error": "conversation not found"}, status=status.HTTP_404_NOT_FOUND)

                # Block if already submitted
                if conv.submitted:
                    return Response({"error": "conversation already submitted"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                conv = ClaimService.create_conversation()

            # ── 2. Save user message ───────────────────────────────────────
            ClaimService.save_user_message(conv, msg)

            # ── 3. Build history + resolve any uploaded files ──────────────
            history = ClaimService.get_conversation_history(conv)
            file_messages = ClaimService.get_conversation_files(conv)

            handler = _get_handler(prompt)
            uploads = _resolve_uploads(handler, file_messages)

            # ── 4. Call AI ─────────────────────────────────────────────────
            resp = handler.push_message(
                payload={"conversation": history, "current_state": conv.state_json},
                uploads=uploads if uploads else None,
            )

            raw = resp["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            try:
                ai_response = json.loads(raw)
            except json.JSONDecodeError:
                try:
                    last_brace = raw.rfind("}")
                    if last_brace != -1:
                        ai_response = json.loads(raw[:last_brace + 1])
                    else:
                        raise ValueError("No closing brace found")
                except Exception as e:
                    return Response({"error": f"AI returned truncated JSON: {str(e)}", "raw": raw}, status=status.HTTP_502_BAD_GATEWAY)

            is_summary = ai_response.get("summary") == "true"
            ai_msg = "Your FNOL is complete." if is_summary else ai_response.get("message", "")

            # ── 5. Save assistant reply + update state ─────────────────────
            ClaimService.save_assistant_message(conv, ai_msg)
            ClaimService.update_state(conv, ai_response)

            # ── 6. Return ──────────────────────────────────────────────────
            return Response({
                "conv_id": str(conv.uid),
                "reply": ai_msg,
                "summary": is_summary,
                "data": conv.summary if is_summary else None,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("===ERROR : ", traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class ClaimsFileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, conv_id: uuid.UUID):
        try:
            conv = ClaimService.get_conversation(conv_id)
            if not conv:
                return Response({"error": "conversation not found"}, status=status.HTTP_404_NOT_FOUND)

            # Block if already submitted
            if conv.submitted:
                return Response({"error": "conversation already submitted"}, status=status.HTTP_400_BAD_REQUEST)

            file = request.FILES.get("file")
            if not file:
                return Response({"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

            caption = (request.data.get("caption") or "").strip() or None

            file_uuid = uuid.uuid4()
            os.makedirs(TMP_DIR, exist_ok=True)
            local_path = os.path.join(TMP_DIR, str(file_uuid))
            with open(local_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)

            ClaimService.save_file_message(
                conv,
                file_id=file_uuid,
                filename=file.name,
                content_type=file.content_type,
                message=caption,
                provider_file_id=None,
            )

            return Response({
                "file_uid": str(file_uuid),
                "filename": file.name,
                "content_type": file.content_type,
                "size": file.size,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)