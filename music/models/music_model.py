from django.db import models

# Create your models here.
# models.py
class Music(models.Model):
    title = models.CharField(max_length=100)
    album_id = models.CharField(max_length=100)
    album_title = models.CharField(max_length=100)
    artist = models.CharField(max_length=100)
    cover = models.ImageField(upload_to='media/music/covers/', default='')
    audio = models.FileField(upload_to='media/music/audio/')  # ← 真正存 mp3
    url = models.CharField(max_length=200, default='')   # 可做外链备用
