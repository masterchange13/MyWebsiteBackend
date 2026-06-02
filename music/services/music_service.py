from music.models.music_model import Music
from django.http import JsonResponse, FileResponse
from users.models.user_model import User
import os


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()


def _to_api_url(path: str):
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    if path.startswith('/api/'):
        return path
    if path.startswith('/'):
        return f'/api{path}'
    return f'/api/{path}'


def _cover_fallback(music_id: int):
    seed = f'music-{music_id}'
    return f'https://picsum.photos/seed/{seed}/320/320'


def _serialize_music(m: Music):
    url = (m.url or '').strip()
    if not url:
        try:
            filename = os.path.basename(m.audio.name or '')
            if filename:
                url = f'/api/media/music/audio/{filename}'
        except Exception:
            url = ''
    else:
        url = _to_api_url(url)

    cover_url = ''
    try:
        filename = os.path.basename(m.cover.name or '')
        if filename:
            cover_url = f'/api/media/music/covers/{filename}'
    except Exception:
        cover_url = ''
    if not cover_url:
        cover_url = _cover_fallback(m.id)

    return {
        'id': m.id,
        'title': m.title,
        'name': m.title,
        'artist': m.artist,
        'album_id': m.album_id or '',
        'album_title': m.album_title or '',
        'cover': cover_url,
        'url': url,
    }

def get_music_list(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    musics = Music.objects.filter(user=u).order_by('-id')
    return JsonResponse({'code': 200, 'message': '音乐列表获取成功', 'data': [_serialize_music(m) for m in musics]})

def add_music(request):
    return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}}, status=405)

def get_all_music(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    musics = Music.objects.filter(user=u).order_by('-id')
    return JsonResponse({'code': 200, 'message': '音乐列表获取成功', 'data': [_serialize_music(m) for m in musics]})

def delete_music(request):
    music = Music.objects.get(id=request.POST['id'])
    music.delete()
    return JsonResponse({'code': 200, 'message': '音乐删除成功', 'data': {}})

def upload_music(request):
    if request.method == 'POST':
        u = _get_request_user(request)
        if not u:
            return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

        title = (request.POST.get('title') or '').strip() or '未命名'
        artist = (request.POST.get('artist') or '').strip() or '未知歌手'
        cover = request.FILES.get('cover')
        audio = request.FILES.get('audio')
        if not audio:
            return JsonResponse({'code': 400, 'message': 'audio is required', 'data': {}}, status=400)

        music = Music.objects.create(
            user=u,
            title=title,
            album_id='',
            album_title='',
            artist=artist,
            cover=cover or '',
            audio=audio,
            url='',
        )

        return JsonResponse({'code': 200, 'message': '音乐上传成功', 'data': _serialize_music(music)})

# media
def get_audio(request, filename):
    return FileResponse(open(f'media/music/audio/{filename}', 'rb'), content_type='audio/mpeg')

def get_cover(request, filename):
    return FileResponse(open(f'media/music/covers/{filename}', 'rb'), content_type='image/jpeg')
