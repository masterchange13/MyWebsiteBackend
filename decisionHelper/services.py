import json

from django.http import JsonResponse

from decisionHelper.models import DecisionHistory
from users.models.user_model import User


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def record_decision(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    data = json.loads(request.body or '{}')
    decision_type = data.get('type', '').strip()
    result = data.get('result', '')
    detail = data.get('detail', '')

    valid_types = dict(DecisionHistory.TYPE_CHOICES)
    if decision_type not in valid_types:
        return JsonResponse({'code': 400, 'message': 'invalid type', 'data': {}})

    DecisionHistory.objects.create(
        user=u,
        type=decision_type,
        result=str(result),
        detail=str(detail),
    )

    return JsonResponse({'code': 200, 'message': 'recorded', 'data': {}})


def get_history(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)

    limit = int(request.GET.get('limit', 20))
    limit = max(1, min(limit, 100))

    qs = DecisionHistory.objects.filter(user=u).order_by('-created_at')[:limit]
    data = list(qs.values('id', 'type', 'result', 'detail', 'created_at'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def clear_history(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    DecisionHistory.objects.filter(user=u).delete()
    return JsonResponse({'code': 200, 'message': 'cleared', 'data': {}})
