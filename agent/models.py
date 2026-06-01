from django.db import models
from users.models.user_model import User

class AgentConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='agent_conversations')
    title = models.CharField(max_length=120, default='新对话')
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)


class AgentMessage(models.Model):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_SYSTEM = 'system'
    ROLE_CHOICES = [
        (ROLE_USER, 'user'),
        (ROLE_ASSISTANT, 'assistant'),
        (ROLE_SYSTEM, 'system'),
    ]

    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
