from django.shortcuts import render
from music.services import music_service

# urlpatten = [
#     path('list', views.get_music_list),
#     path('add', views.add_music),
#     path('update', views.update_music),
#     path('remove', views.remove_music),
#     path('get_all', views.get_all_music),
#     path('update_music_status', views.update_music_status),
#     path('upload', views.upload_music),
# ]

# Create your views here.
def get_music_list(request):
    data = music_service.get_music_list(request)
    return data

def add_music(request):
    data = music_service.add_music(request)
    return data

def update_music(request):
    data = music_service.update_music(request)
    return data

def remove_music(request):
    data = music_service.remove_music(request)
    return data

def update_music_status(request):
    data = music_service.update_music_status(request)
    return data

def get_all_music(request):
    data = music_service.get_all_music(request)
    return data

def delete_music(request):
    data = music_service.delete_music(request)
    return data

def upload_music(request):
    data = music_service.upload_music(request)
    return data


# media
# media_url = [
#     path('audio/<str:filename>'),
#     path('covers/<str:filename>')
# ]
# Create your views here.
def get_audio(request, filename):
    data = music_service.get_audio(request, filename)
    return data

def get_cover(request, filename):
    data = music_service.get_cover(request, filename)
    return data