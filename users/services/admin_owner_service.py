from django.http import JsonResponse
from users.models.user_model import User
from users.models.navigator_model import Navigator
from to_do_list.models.to_do_list_model import ToDoList
from document.models.document_model import Document
from music.models.music_model import Music

def assign_admin_owner(request):
    username = request.GET.get('username') or request.POST.get('username') or 'admin'
    admin = User.objects.filter(username=username).first()
    if not admin:
        email = f'{username}@local'
        # 确保唯一邮箱
        if User.objects.filter(email=email).exists():
            email = f'{username}+owner@local'
        admin = User.objects.create(username=username, password='', email=email)
    updated_counts = {
        'navigator': Navigator.objects.filter(user__isnull=True).update(user=admin),
        'todo': ToDoList.objects.filter(user__isnull=True).update(user=admin),
        'document': Document.objects.filter(user__isnull=True).update(user=admin),
        'music': Music.objects.filter(user__isnull=True).update(user=admin),
    }
    return JsonResponse({'code': 200, 'message': 'ownership assigned', 'data': {'username': admin.username, 'updated': updated_counts}})
