import json
from django.http import JsonResponse, HttpResponse
from users.models.user_model import User

def test(request):
    return HttpResponse('<h1> hello test')

# 用户登录功能函数
# 该函数用于处理用户的登录请求
# 参数:
#     request: 包含用户请求信息的对象，可能包含用户名、密码等信息
def login(request):
    data = json.loads(request.body)

    username = data.get('username')
    password = data.get('password')

    ret = User.objects.get(username=username, password=password)

    if ret:
        request.session['user'] = username   # 建立 session
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'msg': '用户名或密码错误'}, status=400)

def get_me(request):
    user = request.session.get('user')
    if user:
        return JsonResponse({'code': 200, 'message': 'success', 'data': user})
    else:
        return JsonResponse({'code': 400, 'message': '未登录'}, status=400)

def get_user_detail(request):
    username = request.GET.get('username') or request.GET.get('name')
    if not username:
        return JsonResponse({'code': 400, 'message': 'username is required'}, status=400)
    try:
        u = User.objects.get(username=username)
        data = {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'created_time': u.created_time,
        }
        return JsonResponse({'code': 200, 'message': 'success', 'data': data})
    except User.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '用户不存在'}, status=404)
