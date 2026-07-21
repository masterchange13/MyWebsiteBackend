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


class WebsiteSetting(models.Model):
    key = models.CharField(max_length=50, unique=True, default='default')
    site_title = models.CharField(max_length=120, default='Raspberrypi Console')
    login_title = models.CharField(max_length=120, default='欢迎回来')
    login_slogan = models.CharField(max_length=255, default='快速进入你的个人聚合空间')
    theme = models.CharField(max_length=50, default='cyber')
    density = models.CharField(max_length=50, default='balanced')
    surface_style = models.CharField(max_length=50, default='glass')
    corner_style = models.CharField(max_length=50, default='soft')
    font_scale = models.CharField(max_length=50, default='normal')
    show_petals = models.BooleanField(default=True)
    top_level_order = models.JSONField(default=list)
    submenu_orders = models.JSONField(default=dict)
    created_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
