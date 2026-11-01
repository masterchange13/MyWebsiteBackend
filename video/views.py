from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET
import time
from channels.db import database_sync_to_async

from video.camera import CameraError, camera_manager, stream_frames, async_stream_frames
from users.models.user_model import User
from users.access import refresh_user


def _get_request_user(request):
    username = request.session.get('user')
    return User.objects.filter(username=username).first() if username else None


def _authorize(request):
    user = _get_request_user(request)
    if not user:
        return JsonResponse({'code': 401, 'message': '请先登录后查看摄像头。', 'data': {}}, status=401)
    if not user.is_advanced:
        return JsonResponse({'code': 403, 'message': '摄像头仅限高级用户使用，请联系管理员。', 'data': {}}, status=403)
    return None


def _stream_permission(request):
    last_check = time.monotonic()

    def check():
        nonlocal last_check
        now = time.monotonic()
        if now - last_check < 5:
            return True
        user = refresh_user(request.session)
        last_check = now
        return bool(user and user.is_advanced)

    return check


@require_GET
def video_status(request):
    error = _authorize(request)
    if error is not None:
        return error
    try:
        data = camera_manager.inspect() if request.GET.get('check_only') == '1' else camera_manager.prepare()
    except CameraError as error:
        return JsonResponse({'code': 503, 'message': str(error), 'data': {}}, status=503)
    return JsonResponse({'code': 200, 'message': '摄像头已连接', 'data': data})


@require_GET
def video_feed(request):
    error = _authorize(request)
    if error is not None:
        return error
    try:
        camera_manager.prepare()
    except CameraError as error:
        return JsonResponse({'code': 503, 'message': str(error), 'data': {}}, status=503)
    check = _stream_permission(request)
    frames = (async_stream_frames(camera_manager, database_sync_to_async(check))
              if hasattr(request, 'scope') else stream_frames(camera_manager, check))
    response = StreamingHttpResponse(frames, content_type='multipart/x-mixed-replace; boundary=frame')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response['X-Accel-Buffering'] = 'no'
    return response
