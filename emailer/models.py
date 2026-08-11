from django.db import models
from users.models.user_model import User


class SmtpConfig(models.Model):
    """用户 SMTP 配置，每个用户一条记录"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='smtp_config', null=True, blank=True)
    host = models.CharField(max_length=255, default='smtp.qq.com')
    port = models.IntegerField(default=465)
    use_ssl = models.BooleanField(default=True)
    username = models.CharField(max_length=255, blank=True, default='')
    password = models.CharField(max_length=255, blank=True, default='')
    sender_name = models.CharField(max_length=100, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)


class EmailHistory(models.Model):
    """发送历史"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_histories', null=True, blank=True)
    to_email = models.CharField(max_length=500)
    subject = models.CharField(max_length=500)
    body = models.TextField(blank=True, default='')
    success = models.BooleanField(default=True)
    error_msg = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
