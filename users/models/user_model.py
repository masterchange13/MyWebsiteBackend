from django.db import models

# model.py
class User(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_time = models.DateTimeField(auto_now_add=True)
    is_advanced = models.BooleanField(
        default=False, verbose_name='高级用户',
        help_text='高级用户可使用服务器摄像头和终端；未勾选为普通用户。',
    )
