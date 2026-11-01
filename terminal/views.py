import uuid
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from terminal.access import current_user, allowed
from terminal.console import configuration


def _authorize(request):
    user = current_user(request.session)
    if not user:
        return None, JsonResponse({'code': 401, 'message': '请先登录。', 'data': {}}, status=401)
    if not allowed(user):
        return None, JsonResponse({'code': 403, 'message': '终端仅限高级用户使用，或管理员已关闭终端功能。', 'data': {}}, status=403)
    return user, None


@require_GET
def status(request):
    user, error = _authorize(request)
    if error is not None:
        return error
    try:
        info = configuration()
    except ValueError as error:
        return JsonResponse({'code': 503, 'message': str(error), 'data': {}}, status=503)
    info.pop('args')
    info['shell'] = Path(info['shell']).name
    info['active_connection'] = bool(cache.get(f'terminal-session:{user.pk}'))
    response = JsonResponse({'code': 200, 'data': info})
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def close_session(request):
    user, error = _authorize(request)
    if error is not None:
        return error
    lease_id = cache.get(f'terminal-session:{user.pk}')
    if lease_id:
        # Target this connection only: a later connection must not inherit the request.
        cache.set(f'terminal-stop:{lease_id}', True, settings.TERMINAL_IDLE_TIMEOUT + 60)
    response = JsonResponse({'code': 200, 'data': {'closing': bool(lease_id)}})
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def create_session(request):
    user, error = _authorize(request)
    if error is not None:
        return error
    token = signing.dumps({
        'uid': user.pk, 'sid': request.session.session_key,
        'nonce': uuid.uuid4().hex,
    }, salt='website-terminal')
    response = JsonResponse({'code': 200, 'data': {'token': token, 'expires_in': 60}})
    response['Cache-Control'] = 'no-store'
    return response
