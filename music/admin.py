from django.contrib import admin
from music.models.music_model import Music

@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'artist', 'album_title', 'user')
    search_fields = ('title', 'artist', 'user__username')
