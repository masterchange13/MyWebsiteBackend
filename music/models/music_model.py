from django.db import models

# Create your models here.
class Music(models.Model):
    title = models.CharField(max_length=100)
    album_id = models.CharField(max_length=100)
    album_title = models.CharField(max_length=100)
    artist = models.CharField(max_length=100)
    # genre = models.CharField(max_length=100)
    cover = models.ImageField(upload_to='music/', default='')
    # duration = models.IntegerField()
    # file = models.FileField(upload_to='music/')
    url = models.CharField(max_length=200, default='')