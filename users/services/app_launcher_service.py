import json
import subprocess
import shlex

from django.http import JsonResponse
from django.db import transaction
from django.db.models import Max

from users.models.app_launcher_model import AppLauncher
from users.models.user_model import User


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _qs_for_user(u):
    return AppLauncher.objects.filter(user=u)


def _normalize_img(img):
    if img is None:
        return ''
    img = str(img).strip()
    return img


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


def get_all_app_launchers(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    qs = _qs_for_user(u).order_by('display_order', 'id')
    data = list(qs.values('id', 'name', 'img', 'link', 'display_order'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def save_app_launcher(request):
    data = json.loads(request.body or '{}')
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    img = _normalize_img(data.get('img'))
    link = data.get('link', '').strip()
    if not link:
        return JsonResponse({'code': 400, 'message': 'link is required', 'data': {}})
    max_order = _qs_for_user(u).aggregate(m=Max('display_order')).get('m')
    next_order = (max_order + 1) if max_order is not None else 0
    AppLauncher.objects.create(
        user=u,
        name=data.get('name', ''),
        img=img,
        link=link,
        display_order=next_order,
    )
    return JsonResponse({'code': 200, 'message': 'App saved successfully', 'data': {}})


def update_app_launcher(request):
    data = json.loads(request.body or '{}')
    app_id = data.get('id')
    if not app_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    qs = _qs_for_user(u).filter(id=app_id)
    app = qs.first()
    if not app:
        return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

    app.name = data.get('name', app.name)
    app.link = data.get('link', app.link)
    app.img = _normalize_img(data.get('img', app.img))
    app.save(update_fields=['name', 'link', 'img'])
    return JsonResponse({'code': 200, 'message': 'updated', 'data': {}})


def remove_app_launcher(request):
    try:
        raw = request.body or b''
        data = json.loads(raw.decode('utf-8')) if raw else {}
    except Exception:
        data = {}
    app_id = data.get('id') or request.GET.get('id')
    if not app_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    with transaction.atomic():
        _qs_for_user(u).filter(id=app_id).delete()
        _normalize_display_orders(u)

    return JsonResponse({'code': 200, 'message': 'App removed successfully', 'data': {}})


def insert_app_launcher_order(request):
    data = json.loads(request.body or '{}')
    app_id = data.get('id')
    target_index = data.get('target_index')

    if not app_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})
    if target_index is None:
        return JsonResponse({'code': 400, 'message': 'target_index is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    with transaction.atomic():
        items = _normalize_display_orders(u)
        id_list = [item.id for item in items]
        if app_id not in id_list:
            return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

        from_index = id_list.index(app_id)
        max_index = len(items) - 1
        target_index = max(0, min(int(target_index), max_index))
        if from_index == target_index:
            return JsonResponse({'code': 200, 'message': 'order unchanged', 'data': {}})

        _move_item(items, from_index, target_index)

    return JsonResponse({'code': 200, 'message': 'order inserted', 'data': {}})


def swap_app_launcher_order(request):
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


def launch_app(request):
    """Launch a desktop application by executing its link as a shell command on the server."""
    data = json.loads(request.body or '{}')
    app_id = data.get('id')
    if not app_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    app = _qs_for_user(u).filter(id=app_id).first()
    if not app:
        return JsonResponse({'code': 404, 'message': 'app not found', 'data': {}})

    shell_command = app.link.strip()
    if not shell_command:
        return JsonResponse({'code': 400, 'message': 'link is empty', 'data': {}})

    try:
        subprocess.Popen(
            shlex.split(shell_command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return JsonResponse({'code': 200, 'message': f'Launched: {app.name}', 'data': {}})
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'Failed to launch: {str(e)}', 'data': {}})
