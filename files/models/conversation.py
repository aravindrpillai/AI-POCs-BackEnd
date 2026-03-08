import uuid
from django.db import models
from django.utils import timezone
from .file_conversation import FileConversation


class Conversation(models.Model):

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_conversation = models.ForeignKey(FileConversation, on_delete=models.CASCADE, related_name='conversations')
    role = models.CharField(max_length=10, choices=Role.choices, default='user')
    content = models.TextField(default='')
    references = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role} — {self.file_conversation.conv_id}'