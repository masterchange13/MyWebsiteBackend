from django.db import models
from users.models.user_model import User

class QimenCalculation(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='qimen_calculations')
    datetime_str = models.CharField(max_length=32, blank=True)
    location = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    solar = models.BooleanField(default=True)
    parsed_datetime = models.DateTimeField(null=True, blank=True)
    seed = models.BigIntegerField(default=0)
    analysis_text = models.TextField(blank=True)
    analysis_provider = models.CharField(max_length=64, blank=True)
    analysis_model = models.CharField(max_length=64, blank=True)
    analysis_time = models.DateTimeField(null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True)

class QimenPalace(models.Model):
    calc = models.ForeignKey(QimenCalculation, on_delete=models.CASCADE, related_name='palaces')
    index = models.PositiveSmallIntegerField()
    gate = models.CharField(max_length=8)
    star = models.CharField(max_length=16)
    god = models.CharField(max_length=16)
    tip = models.CharField(max_length=255, blank=True)
