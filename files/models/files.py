import uuid
from django.db import models
from .file_conversation import FileConversation


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_conversation = models.ForeignKey(FileConversation, on_delete=models.CASCADE, related_name='files')
    file_name = models.CharField(max_length=255)
    extension = models.CharField(max_length=20)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name