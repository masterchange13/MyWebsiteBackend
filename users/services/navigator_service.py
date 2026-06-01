from django.http import JsonResponse
from users.models.navigator_model import Navigator
from users.models.user_model import User
import json
from urllib.parse import urlparse
from django.db import transaction
from django.db.models import Max

def _get_request_user(request):
    username = request.session.get('user') or request.GET.get('username') or request.POST.get('username')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

def _qs_for_user(u):
    if u:
        return Navigator.objects.filter(user=u)
    return Navigator.objects.filter(user__isnull=True)

def _default_favicon(url):
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            parsed = urlparse(f'https://{url}')
        if not parsed.scheme or not parsed.netloc:
            return ''
        origin = f'{parsed.scheme}://{parsed.netloc}'
        return f'{origin}/favicon.ico'
    except Exception:
        return ''

def _normalize_img(img, url):
    if img is None:
        img = ''
    img = str(img).strip()
    if img:
        return img
    return _default_favicon(url)

def get_all_navigators(request):
    u = _get_request_user(request)
    qs = _qs_for_user(u).order_by('display_order', 'id')
    data = list(qs.values('id', 'name', 'img', 'url', 'display_order'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})

def save_icon(request):
    data = json.loads(request.body or '{}')   # ⭐ 关键
    u = _get_request_user(request)
    img = _normalize_img(data.get('img'), data.get('url'))
    max_order = _qs_for_user(u).aggregate(m=Max('display_order')).get('m')
    next_order = (max_order + 1) if max_order is not None else 0
    Navigator.objects.create(
        user=u,
        name=data.get('name'),
        img=img,
        url=data.get('url'),
        display_order=next_order,
    )
    return JsonResponse({'code': 200, 'message': 'Icon saved successfully', 'data': {}})

def add_icon(request):
    return save_icon(request)

def update_icon(request):
    data = json.loads(request.body or '{}')
    navigator_id = data.get('id')
    if not navigator_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})

    u = _get_request_user(request)
    qs = _qs_for_user(u).filter(id=navigator_id)
    nav = qs.first()
    if not nav:
        return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

    name = data.get('name', nav.name)
    url = data.get('url', nav.url)
    img = _normalize_img(data.get('img', nav.img), url)

    nav.name = name
    nav.url = url
    nav.img = img
    nav.save(update_fields=['name', 'url', 'img'])
    return JsonResponse({'code': 200, 'message': 'updated', 'data': {}})

def update_navigator_order(request):
    data = json.loads(request.body or '{}')
    ordered_ids = data.get('ordered_ids') or data.get('orderedIds')
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return JsonResponse({'code': 400, 'message': 'ordered_ids is required', 'data': {}})

    u = _get_request_user(request)
    existing = set(_qs_for_user(u).filter(id__in=ordered_ids).values_list('id', flat=True))

    with transaction.atomic():
        for order, nav_id in enumerate(ordered_ids):
            if nav_id in existing:
                _qs_for_user(u).filter(id=nav_id).update(display_order=order)

    return JsonResponse({'code': 200, 'message': 'order updated', 'data': {}})

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
    _qs_for_user(u).filter(id=navigator_id).delete()
    return JsonResponse({'code': 200, 'message': 'Icon removed successfully', 'data': {}})
