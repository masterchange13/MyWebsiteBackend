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
    username = request.session.get('user') or request.GET.get('username') or request.POST.get('username')
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
    qs = Feedback.objects.all().order_by('-created_time')
    if request.GET.get('all') == '1':
        if not (u and u.username == 'admin'):
            return JsonResponse({'code': 403, 'message': 'forbidden', 'data': []})
    else:
        if u:
            qs = qs.filter(user=u)
        else:
            return JsonResponse({'code': 200, 'message': 'success', 'data': []})

    data = list(
        qs.values(
            'id',
            'title',
            'content',
            'contact',
            'status',
            'reply',
            'created_time',
            'update_time',
        )
    )
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})
