from django.http import JsonResponse
from users.models.navigator_model import Navigator
from users.models.user_model import User
import json
from urllib.parse import urlparse
from django.db import transaction
from django.db.models import Max


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _qs_for_user(u):
    return Navigator.objects.filter(user=u)


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


def _normalize_display_orders(u):
    items = list(_qs_for_user(u).order_by('display_order', 'id'))
    for index, item in enumerate(items):
        if item.display_order != index:
            item.display_order = index
            item.save(update_fields=['display_order'])
    return items


def _move_item(items, from_index, to_index):
    item = items.pop(from_index)
    items.insert(to_index, item)
    for index, nav in enumerate(items):
        nav.display_order = index
        nav.save(update_fields=['display_order'])


def get_all_navigators(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    qs = _qs_for_user(u).order_by('display_order', 'id')
    data = list(qs.values('id', 'name', 'img', 'url', 'display_order'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def save_icon(request):
    data = json.loads(request.body or '{}')
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
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
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
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
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    existing = set(_qs_for_user(u).filter(id__in=ordered_ids).values_list('id', flat=True))
    if len(existing) != len(ordered_ids):
        return JsonResponse({'code': 400, 'message': 'ordered_ids contains invalid ids', 'data': {}})

    with transaction.atomic():
        for order, nav_id in enumerate(ordered_ids):
            _qs_for_user(u).filter(id=nav_id).update(display_order=order)

    return JsonResponse({'code': 200, 'message': 'order updated', 'data': {}})


def insert_navigator_order(request):
    data = json.loads(request.body or '{}')
    navigator_id = data.get('id')
    target_index = data.get('target_index')

    if not navigator_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})
    if target_index is None:
        return JsonResponse({'code': 400, 'message': 'target_index is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    with transaction.atomic():
        items = _normalize_display_orders(u)
        id_list = [item.id for item in items]
        if navigator_id not in id_list:
            return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

        from_index = id_list.index(navigator_id)
        max_index = len(items) - 1
        target_index = max(0, min(int(target_index), max_index))
        if from_index == target_index:
            return JsonResponse({'code': 200, 'message': 'order unchanged', 'data': {}})

        _move_item(items, from_index, target_index)

    return JsonResponse({'code': 200, 'message': 'order inserted', 'data': {}})


def swap_navigator_order(request):
    data = json.loads(request.body or '{}')
    source_id = data.get('source_id')
    target_id = data.get('target_id')

    if not source_id or not target_id:
        return JsonResponse({'code': 400, 'message': 'source_id and target_id are required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    with transaction.atomic():
        items = _normalize_display_orders(u)
        items_by_id = {item.id: item for item in items}
        source = items_by_id.get(source_id)
        target = items_by_id.get(target_id)
        if not source or not target:
            return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

        source_order = source.display_order
        target_order = target.display_order
        if source_order == target_order:
            return JsonResponse({'code': 200, 'message': 'order unchanged', 'data': {}})

        source.display_order = target_order
        target.display_order = source_order
        source.save(update_fields=['display_order'])
        target.save(update_fields=['display_order'])

    return JsonResponse({'code': 200, 'message': 'order swapped', 'data': {}})


def remove_icon(request):
    try:
        raw = request.body or b''
        data = json.loads(raw.decode('utf-8')) if raw else {}
    except Exception:
        data = {}
    navigator_id = data.get('id') or request.GET.get('id')
    if not navigator_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    with transaction.atomic():
        _qs_for_user(u).filter(id=navigator_id).delete()
        _normalize_display_orders(u)

    return JsonResponse({'code': 200, 'message': 'Icon removed successfully', 'data': {}})
