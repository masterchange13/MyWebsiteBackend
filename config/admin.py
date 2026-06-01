from django.contrib import admin
from config.models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'user', 'created_time', 'update_time')
    list_filter = ('status',)
    search_fields = ('title', 'content', 'contact', 'user__username')
