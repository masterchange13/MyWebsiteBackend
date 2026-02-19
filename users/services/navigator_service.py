from django.http import JsonResponse
from users.models.navigator_model import Navigator
from users.models.user_model import User
import json
from django.http import JsonResponse
from users.models.navigator_model import Navigator

def _get_request_user(request):
    username = request.session.get('user') or request.GET.get('username') or request.POST.get('username')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

def get_all_navigators(request):
    u = _get_request_user(request)
    qs = Navigator.objects.all()
    if u:
        qs = qs.filter(user=u)
    data = list(qs.values('id', 'name', 'img', 'url'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})

def save_icon(request):
    data = json.loads(request.body or '{}')   # ⭐ 关键
    u = _get_request_user(request)
    Navigator.objects.create(
        user=u,
        name=data.get('name'),
        img=data.get('img'),
        url=data.get('url')
    )
    return JsonResponse({'code': 200, 'message': 'Icon saved successfully', 'data': {}})

def remove_icon(request):
    try:
        raw = request.body or b''
        data = json.loads(raw.decode('utf-8')) if raw else {}
    except Exception as e:
        data = {}
    navigator_id = data.get('id') or request.GET.get('id')
    if not navigator_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})
    u = _get_request_user(request)
    qs = Navigator.objects.filter(id=navigator_id)
    if u:
        qs = qs.filter(user=u)
    qs.delete()
    return JsonResponse({'code': 200, 'message': 'Icon removed successfully', 'data': {}})
