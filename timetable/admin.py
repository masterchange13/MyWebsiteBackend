from django.contrib import admin
from timetable.models.timetable_model import TimetableEntry
from timetable.models.timetable_config_model import TimetableConfig

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'day_of_week', 'start_period', 'end_period', 'location', 'week_start', 'week_end', 'week_type', 'created_time')
    list_filter = ('day_of_week', 'week_type')
    search_fields = ('name', 'teacher', 'location', 'user__username')

@admin.register(TimetableConfig)
class TimetableConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'updated_time')
