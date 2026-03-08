import uuid
from django.db import models


class FileConversation(models.Model):
    conv_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.conv_id)