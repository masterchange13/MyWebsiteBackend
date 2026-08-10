from django.db import models
from users.models.user_model import User


class AppLauncher(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_launchers', null=True, blank=True)
    name = models.CharField(max_length=255)
    link = models.CharField(max_length=1024)
    img = models.CharField(max_length=1024, blank=True, default='')
    display_order = models.IntegerField(default=0, db_index=True)
