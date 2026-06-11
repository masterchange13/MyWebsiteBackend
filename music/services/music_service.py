from music.models.music_model import Music
from django.http import JsonResponse, FileResponse
from users.models.user_model import User
import os
import json


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


def update_music(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}}, status=405)
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    import json
    data = json.loads(request.body or '{}')
    music_id = data.get('id')
    if not music_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}}, status=400)
    try:
        m = Music.objects.get(id=music_id, user=u)
    except Music.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '音乐不存在', 'data': {}}, status=404)

    if data.get('title'):
        m.title = data['title']
    if data.get('artist'):
        m.artist = data['artist']
    if data.get('album_title') is not None:
        m.album_title = data.get('album_title', '')
    m.save(update_fields=[f for f in ['title', 'artist', 'album_title'] if data.get(f)])
    return JsonResponse({'code': 200, 'message': '更新成功', 'data': _serialize_music(m)})


def remove_music(request):
    if request.method != 'DELETE':
        return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}}, status=405)
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    try:
        body = json.loads(request.body or '{}')
    except Exception:
        body = {}
    music_id = body.get('id')
    if not music_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}}, status=400)
    try:
        m = Music.objects.get(id=music_id, user=u)
    except Music.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '音乐不存在', 'data': {}}, status=404)
    # 删除关联的文件
    if m.audio:
        try:
            os.remove(m.audio.path)
        except Exception:
            pass
    if m.cover:
        try:
            os.remove(m.cover.path)
        except Exception:
            pass
    m.delete()
    return JsonResponse({'code': 200, 'message': '删除成功', 'data': {}})


def update_music_status(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}}, status=405)
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    try:
        body = json.loads(request.body or '{}')
    except Exception:
        body = {}
    music_id = body.get('id')
    if not music_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}}, status=400)
    try:
        m = Music.objects.get(id=music_id, user=u)
    except Music.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '音乐不存在', 'data': {}}, status=404)
    # status 预留：后续可扩展收藏/播放次数等
    return JsonResponse({'code': 200, 'message': '状态更新成功', 'data': _serialize_music(m)})

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


def search_music(request):
    """代理 NetEase Cloud Music 搜索 API"""
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}}, status=405)
    keywords = request.GET.get('keywords', '')
    limit = request.GET.get('limit', '30')
    offset = request.GET.get('offset', '0')
    if not keywords:
        return JsonResponse({'code': 400, 'message': 'keywords is required', 'data': {}}, status=400)
    try:
        import urllib.request
        import urllib.parse
        params = urllib.parse.urlencode({
            'keywords': keywords,
            'limit': limit,
            'offset': offset,
            'type': '1',
        })
        url = f'http://music.163.com/api/search/pc?{params}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return JsonResponse({'code': 200, 'message': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'搜索失败: {str(e)}', 'data': {}}, status=500)


# media
def get_audio(request, filename):
    return FileResponse(open(f'media/music/audio/{filename}', 'rb'), content_type='audio/mpeg')

def get_cover(request, filename):
    return FileResponse(open(f'media/music/covers/{filename}', 'rb'), content_type='image/jpeg')
