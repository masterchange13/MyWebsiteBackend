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
