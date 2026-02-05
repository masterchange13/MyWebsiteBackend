from music.models.music_model import Music

def add_music(request):
    music = Music.objects.create(
        title=request.POST['title'],
        album_id=request.POST['album_id'],
        album_title=request.POST['album_title'],
        artist=request.POST['artist'],
        cover=request.POST['cover'],
        url=request.POST['url'],
    )
    return music

def get_all_music(request):
    musics = Music.objects.all()
    return musics

def delete_music(request):
    music = Music.objects.get(id=request.POST['id'])
    music.delete()
    return music