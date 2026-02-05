from django.shortcuts import render
from music.services import music_service

# Create your views here.
def add_music(request):
    data = music_service.add_music(request)
    return {"code" : 200, "message" : "success", "data" : data}

def get_all_music(request):
    data = music_service.get_all_music(request)
    return {"code" : 200, "message" : "success", "data" : data}

def delete_music(request):
    data = music_service.delete_music(request)
    return {"code" : 200, "message" : "success", "data" : data}