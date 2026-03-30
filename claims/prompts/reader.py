from __future__ import annotations
from datetime import date
from claims.models import ClaimPrompts
from django.conf import settings

class PromptReader:

    @staticmethod
    def get(additional_info = None) -> str:
        # First try to get active prompt
        prompt_obj = ClaimPrompts.objects.filter(active=1).order_by("-updated_on").first()

        # If no active prompt, get latest record
        if not prompt_obj:
            prompt_obj = ClaimPrompts.objects.order_by("-created_on").first()

        if not prompt_obj:
            raise ValueError("No prompt records found in ClaimPrompts table.")

        today = f'TODAY\'S DATE is : {date.today().isoformat()}. Use this as the reference for all relative date calculations'
        prompt = (prompt_obj.prompt or "").strip()
        structure= ""
        with open(f"{settings.BASE_DIR}/claims/prompts/structure.txt", "r", encoding="utf-8") as f:
            structure = f.read()

        final_prompt = f"{today}\n{prompt}\n{structure}"
        
        if(additional_info):
            final_prompt = final_prompt + "\n" + additional_info

        return final_prompt