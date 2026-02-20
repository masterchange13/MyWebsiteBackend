from django.contrib import admin
from chat.models.chat_message_model import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'created_time')
    search_fields = ('sender__username', 'receiver__username',)
