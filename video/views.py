from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

from video.camera import CameraError, camera_manager, stream_frames, async_stream_frames
from users.models.user_model import User


def _get_request_user(request):
    username = request.session.get('user')
    return User.objects.filter(username=username).first() if username else None


@require_GET
def video_status(request):
    if not _get_request_user(request):
        return JsonResponse({'code': 401, 'message': '请先登录后查看摄像头。', 'data': {}}, status=401)
    try:
        data = camera_manager.inspect() if request.GET.get('check_only') == '1' else camera_manager.prepare()
    except CameraError as error:
        return JsonResponse({'code': 503, 'message': str(error), 'data': {}}, status=503)
    return JsonResponse({'code': 200, 'message': '摄像头已连接', 'data': data})


@require_GET
def video_feed(request):
    if not _get_request_user(request):
        return JsonResponse({'code': 401, 'message': '请先登录后查看摄像头。', 'data': {}}, status=401)
    try:
        camera_manager.prepare()
    except CameraError as error:
        return JsonResponse({'code': 503, 'message': str(error), 'data': {}}, status=503)
    frames = async_stream_frames(camera_manager) if hasattr(request, 'scope') else stream_frames(camera_manager)
    response = StreamingHttpResponse(frames, content_type='multipart/x-mixed-replace; boundary=frame')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response['X-Accel-Buffering'] = 'no'
    return response
