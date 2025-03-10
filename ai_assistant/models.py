from django.db import models

from django.db import models


class ChatMapping(models.Model):
    integration = models.CharField(max_length=50)  # Telegram, Slack, Voiceflow
    assistant_id = models.CharField(max_length=100, blank=True, null=True)
    chat_id = models.CharField(max_length=100)
    thread_id = models.CharField(max_length=100, blank=True, null=True)
    date_of_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("integration", "chat_id")

    def __str__(self):
        return f"{self.integration} - {self.chat_id}"
