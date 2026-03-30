import uuid
from django.db import models
from django.core.exceptions import ValidationError

class ClaimPrompts(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    active = models.IntegerField(default=False)
    name = models.CharField(max_length=100, null=False)
    prompt = models.TextField(null=False)
    updated_on = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)



class ClaimConversation(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    state_json = models.JSONField(default=dict)
    state_version = models.IntegerField(default=1)
    summary = models.JSONField(null=True, blank=True, default=None)
    submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ClaimMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "user"),
        ("assistant", "assistant"),
    )

    conversation = models.ForeignKey(ClaimConversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField(null=True, blank=True)

    # File fields
    is_file = models.BooleanField(default=False)
    file_id = models.UUIDField(null=True, blank=True)          # local UUID (filename on disk)
    provider_file_id = models.CharField(max_length=255, null=True, blank=True)  # e.g. file_abc123 from claude/openai
    filename = models.CharField(max_length=255, null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        errors = {}
        if self.is_file:
            if not self.file_id:
                errors["file_id"] = "file_id is required when is_file=True."
            if not self.filename:
                errors["filename"] = "filename is required when is_file=True."
            if not self.content_type:
                errors["content_type"] = "content_type is required when is_file=True."
        else:
            if not self.message or not str(self.message).strip():
                errors["message"] = "message is required when is_file=False."
            if self.file_id:
                errors["file_id"] = "file_id must be empty when is_file=False."
            if self.filename:
                errors["filename"] = "filename must be empty when is_file=False."
            if self.content_type:
                errors["content_type"] = "content_type must be empty when is_file=False."
        if errors:
            raise ValidationError(errors)