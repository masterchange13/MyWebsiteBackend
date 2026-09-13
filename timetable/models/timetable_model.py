from django.db import models
from users.models.user_model import User

class TimetableEntry(models.Model):
    """学生课表条目：一门课程在某星期某节次区间的安排"""

    WEEK_TYPE_CHOICES = [
        ('all', '每周'),
        ('odd', '单周'),
        ('even', '双周'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='timetable_entries', null=True, blank=True)
    name = models.CharField(max_length=120)
    teacher = models.CharField(max_length=120, blank=True, default='')
    location = models.CharField(max_length=120)
    day_of_week = models.SmallIntegerField()      # 1~7
    start_period = models.SmallIntegerField()     # 1~N
    end_period = models.SmallIntegerField()       # >= start_period
    week_start = models.SmallIntegerField(default=1)
    week_end = models.SmallIntegerField(default=16)
    week_type = models.CharField(max_length=10, choices=WEEK_TYPE_CHOICES, default='all')
    color = models.CharField(max_length=20, default='#00f5ff')
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'start_period']

    def __str__(self):
        return self.name
