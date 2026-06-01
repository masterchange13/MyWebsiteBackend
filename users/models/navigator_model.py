from django.db import models
from users.models.user_model import User

class Navigator(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='navigators', null=True, blank=True)
    name = models.CharField(max_length=255)
    img  = models.CharField(max_length=1024, blank=True, default='')
    url = models.CharField(max_length=1024)
    display_order = models.IntegerField(default=0, db_index=True)
