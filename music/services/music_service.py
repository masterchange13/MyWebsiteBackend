from music.models.music_model import Music
from django.http import JsonResponse, FileResponse

def get_music_list(request):
    musics = Music.objects.all()
    return JsonResponse({'code': 200, 'message': '音乐列表获取成功', 'data': list(musics.values())})

def add_music(request):
    music = Music.objects.create(
        title=request.POST['title'],
        album_id=request.POST['album_id'],
        album_title=request.POST['album_title'],
        artist=request.POST['artist'],
        cover=request.POST['cover'],
        url=request.POST['url'],
    )
    return JsonResponse({'code': 200, 'message': '音乐添加成功', 'data': {}})

def get_all_music(request):
    musics = Music.objects.all()

    # for music in musics:
    #     music.cover = 'http://localhost:8083/' + music.cover
    #     music.url = 'http://localhost:8083/' + music.url

    return JsonResponse({'code': 200, 'message': '音乐列表获取成功', 'data': list(musics.values())})

def delete_music(request):
    music = Music.objects.get(id=request.POST['id'])
    music.delete()
    return JsonResponse({'code': 200, 'message': '音乐删除成功', 'data': {}})

def upload_music(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        album_id = request.POST.get('album_id')
        album_title = request.POST.get('album_title')
        artist = request.POST.get('artist')
        cover = request.FILES.get('cover')
        audio = request.FILES.get('audio')

        music = Music.objects.create(
            title=title,
            album_id=album_id,
            album_title=album_title,
            artist=artist,
            cover=cover,
            audio=audio,
            # url=audio.url,
        )

        # 自动生成可访问地址
        music.cover = request.build_absolute_uri(music.cover.url)
        music.url = request.build_absolute_uri(music.audio.url)
        music.save()

        return JsonResponse({'code': 200, 'message': '音乐上传成功', 'music': music.url})

# media
def get_audio(request, filename):
    return FileResponse(open(f'media/music/audio/{filename}', 'rb'), content_type='audio/mpeg')

def get_cover(request, filename):
    return FileResponse(open(f'media/music/covers/{filename}', 'rb'), content_type='image/jpeg')
