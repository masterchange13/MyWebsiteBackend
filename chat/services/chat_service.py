from django.http import JsonResponse
from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage

def get_users(request):
    data = list(User.objects.values('id', 'username', 'email'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})

def get_history(request):
    username = request.GET.get('from') or request.GET.get('username')
    peer = request.GET.get('to') or request.GET.get('peer')
    qs = ChatMessage.objects.all().order_by('-created_time')
    if username:
        user = User.objects.filter(username=username).first()
        if user:
            qs = qs.filter(sender=user) | qs.filter(receiver=user)
    if peer and username:
        user = User.objects.filter(username=username).first()
        puser = User.objects.filter(username=peer).first()
        if user and puser:
            qs = ChatMessage.objects.filter(sender=user, receiver=puser) | ChatMessage.objects.filter(sender=puser, receiver=user)
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
