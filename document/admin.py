from django.contrib import admin
from document.models.document_model import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'user', 'created_time', 'update_time')
    search_fields = ('title', 'author', 'user__username')
