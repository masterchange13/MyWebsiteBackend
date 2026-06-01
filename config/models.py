from django.db import models
from users.models.user_model import User

class Feedback(models.Model):
    STATUS_NEW = 'new'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    title = models.CharField(max_length=120)
    content = models.TextField()
    contact = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    reply = models.TextField(blank=True, default='')
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
