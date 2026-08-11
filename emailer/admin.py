from django.contrib import admin
from emailer.models import SmtpConfig, EmailHistory


@admin.register(SmtpConfig)
class SmtpConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'host', 'port', 'username', 'updated_at')


@admin.register(EmailHistory)
class EmailHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'to_email', 'subject', 'success', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('to_email', 'subject')
