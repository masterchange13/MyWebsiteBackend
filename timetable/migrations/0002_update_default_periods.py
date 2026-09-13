from django.db import migrations

# 学校作息表（第3节按主表 9:45-10:25；午休/课外活动为间隔行不纳入节次）
NEW_PERIODS = [
    {'n': 1, 'start': '08:00', 'end': '08:40'},
    {'n': 2, 'start': '08:45', 'end': '09:25'},
    {'n': 3, 'start': '09:45', 'end': '10:25'},
    {'n': 4, 'start': '10:35', 'end': '11:15'},
    {'n': 5, 'start': '11:20', 'end': '12:00'},
    {'n': 6, 'start': '13:30', 'end': '14:10'},
    {'n': 7, 'start': '14:15', 'end': '14:55'},
    {'n': 8, 'start': '15:15', 'end': '15:55'},
    {'n': 9, 'start': '16:00', 'end': '16:40'},
    {'n': 10, 'start': '18:30', 'end': '19:10'},
    {'n': 11, 'start': '19:15', 'end': '19:55'},
    {'n': 12, 'start': '20:05', 'end': '20:45'},
]


def update_periods(apps, schema_editor):
    TimetableConfig = apps.get_model('timetable', 'TimetableConfig')
    for config in TimetableConfig.objects.all():
        config.periods = NEW_PERIODS
        config.save(update_fields=['periods', 'updated_time'])


class Migration(migrations.Migration):

    dependencies = [
        ('timetable', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_periods, migrations.RunPython.noop),
    ]
