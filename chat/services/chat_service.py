from django.http import JsonResponse

from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage
from chat.services import presence_service


def _serialize_users(online_usernames: set[str]):
    data = []
    for user in User.objects.values('id', 'username', 'email'):
        data.append({
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'online': user['username'] in online_usernames,
        })
    return data


def get_online_users(request):
    """获取当前在线用户列表"""
    username = request.session.get('user')
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    presence_service.touch_user(username)
    online_usernames = presence_service.get_online_usernames()
    return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_users(online_usernames)})

def get_users(request):
    username = request.session.get('user')
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    presence_service.touch_user(username)
    online_usernames = presence_service.get_online_usernames()
    return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_users(online_usernames)})

def get_history(request):
    username = request.session.get('user')
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)

    # 前端传参：{ from: 当前用户名, to: 对方用户名 }
    from_user = request.GET.get('from')
    to_user = request.GET.get('to')
    peer = request.GET.get('peer')

    # 确定双方用户名：优先用 from/to，其次用 username + peer
    user_a = from_user or username
    user_b = to_user or peer

    if not user_a or not user_b:
        return JsonResponse({'code': 400, 'message': '参数缺失', 'data': []}, status=400)

    from_user_obj = User.objects.filter(username=user_a).first()
    to_user_obj = User.objects.filter(username=user_b).first()

    if not from_user_obj or not to_user_obj:
        return JsonResponse({'code': 404, 'message': '用户不存在', 'data': []}, status=404)

    # 只查这两人之间的消息
    qs = (
        ChatMessage.objects.filter(sender=from_user_obj, receiver=to_user_obj)
        | ChatMessage.objects.filter(sender=to_user_obj, receiver=from_user_obj)
    ).order_by('created_time')

    data = [
        {
            'sendUsername': m.sender.username if m.sender else None,
            'receiveUsername': m.receiver.username if m.receiver else None,
            'data': m.content,
            'created_time': m.created_time,
        }
        for m in qs[:200]
    ]
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})
