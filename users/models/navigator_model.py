from django.db import models

class Navigator(models.Model):
    name = models.CharField(max_length=255)
    img  = models.CharField(max_length=255)
    url = models.CharField(max_length=255)