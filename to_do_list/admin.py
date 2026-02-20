from django.contrib import admin
from to_do_list.models.to_do_list_model import ToDoList

@admin.register(ToDoList)
class ToDoListAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'completed', 'user', 'created_time', 'updated_time')
    list_filter = ('completed',)
    search_fields = ('title', 'user__username')
