from django.db import models
from users.models.user_model import User

# Create your models here.
# models.py
class Music(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='musics', null=True, blank=True)
    title = models.CharField(max_length=100)
    album_id = models.CharField(max_length=100)
    album_title = models.CharField(max_length=100)
    artist = models.CharField(max_length=100)
    cover = models.ImageField(upload_to='media/music/covers/', default='')
    audio = models.FileField(upload_to='media/music/audio/')  # ← 真正存 mp3
    url = models.TextField(blank=True)
