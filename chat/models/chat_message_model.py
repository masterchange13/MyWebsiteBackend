from django.db import models
from users.models.user_model import User

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
