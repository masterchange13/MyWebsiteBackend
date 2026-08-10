from django.db import models
from users.models.user_model import User


class DecisionHistory(models.Model):
    TYPE_CHOICES = [
        ('coin', '抛硬币'),
        ('dice', '掷骰子'),
        ('yesno', 'Yes/No'),
        ('random', '随机数'),
        ('pick', '多选一'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decision_histories', null=True, blank=True)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    result = models.CharField(max_length=255)
    detail = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
