from django.db import models

# model.py
class User(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_time = models.DateTimeField(auto_now_add=True)
    can_use_terminal = models.BooleanField(
        default=False, verbose_name='终端权限',
        help_text='允许此网站账号连接服务器终端，命令以运行后端的系统账号身份执行。',
    )
