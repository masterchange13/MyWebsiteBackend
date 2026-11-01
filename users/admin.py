from django.contrib import admin
from users.models.navigator_model import Navigator
from users.models.user_model import User

@admin.register(Navigator)
class NavigatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'user')
    search_fields = ('name', 'url', 'user__username')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_advanced', 'created_time')
    list_editable = ('is_advanced',)
    list_filter = ('is_advanced',)
    search_fields = ('username', 'email')
