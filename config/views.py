from django.shortcuts import render

# Create your views here.
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json

from config.models import Feedback
from users.models.user_model import User

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'code': 200, 'message': 'CSRF cookie set', 'data': {}})

def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()

@require_http_methods(["POST"])
def submit_feedback(request):
    data = json.loads(request.body or '{}')
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    contact = (data.get('contact') or '').strip()
    if not title:
        return JsonResponse({'code': 400, 'message': 'title is required', 'data': {}})
    if not content:
        return JsonResponse({'code': 400, 'message': 'content is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    fb = Feedback.objects.create(
        user=u,
        title=title,
        content=content,
        contact=contact,
    )
    return JsonResponse({'code': 200, 'message': 'success', 'data': {'id': fb.id}})

@require_http_methods(["GET"])
def list_feedback(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    qs = Feedback.objects.select_related('user').all().order_by('-created_time')

    data = []
    for fb in qs[:200]:
        data.append({
            'id': fb.id,
            'title': fb.title,
            'content': fb.content,
            'contact': fb.contact,
            'status': fb.status,
            'reply': fb.reply,
            'username': fb.user.username if fb.user else None,
            'created_time': fb.created_time,
            'update_time': fb.update_time,
        })
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})
