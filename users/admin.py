from django.contrib import admin
from users.models.navigator_model import Navigator
from users.models.user_model import User

@admin.register(Navigator)
class NavigatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'user')
    search_fields = ('name', 'url', 'user__username')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'created_time')
    search_fields = ('username', 'email')
