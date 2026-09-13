from django.db import models
from users.models.user_model import User

class TimetableConfig(models.Model):
    """每用户的节次时间配置：periods = [{'n':1,'start':'08:00','end':'08:45'}, ...]"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='timetable_config')
    periods = models.JSONField(default=list)
    updated_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'TimetableConfig({self.user_id})'
