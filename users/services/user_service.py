import json
from django.http import JsonResponse, HttpResponse
from users.models.user_model import User
from django.contrib.auth.hashers import check_password, make_password

def test(request):
    return HttpResponse('<h1> hello test')

# 用户登录功能函数
# 该函数用于处理用户的登录请求
# 参数:
#     request: 包含用户请求信息的对象，可能包含用户名、密码等信息
def login(request):
    data = json.loads(request.body or '{}')

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return JsonResponse({'code': 400, 'message': '缺少用户名或密码', 'data': {}}, status=400)

    u = User.objects.filter(username=username).first()
    if not u:
        return JsonResponse({'code': 400, 'message': '用户名或密码错误', 'data': {}}, status=400)

    ok = False
    try:
        ok = check_password(password, u.password)
    except Exception:
        ok = False
    if not ok and u.password == password:
        u.password = make_password(password)
        u.save(update_fields=['password'])
        ok = True

    if ok:
        request.session['user'] = username
        return JsonResponse({'code': 200, 'message': 'success', 'data': {}})

    return JsonResponse({'code': 400, 'message': '用户名或密码错误', 'data': {}}, status=400)

def get_me(request):
    user = request.session.get('user')
    if not user:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    u = User.objects.filter(username=user).first()
    if not u:
        request.session.flush()
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    user_id = u.id
    data = {
        'id': user_id,
        'username': user,
        'email': u.email,
        'created_time': u.created_time.isoformat() if u.created_time else None,
    }
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})

def get_user_detail(request, user_id=None):
    if request.method != 'GET':
        return HttpResponse(status=405)

    username = request.GET.get('username') or request.GET.get('name')
    user_id = user_id or request.GET.get('id')
    if not username and not user_id:
        return JsonResponse({'code': 400, 'message': 'id or username is required', 'data': {}}, status=400)
    try:
        if user_id:
            u = User.objects.get(id=user_id)
        else:
            u = User.objects.get(username=username)
        data = {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'created_time': u.created_time.isoformat() if u.created_time else None,
        }
        return JsonResponse({'code': 200, 'message': 'success', 'data': data})
    except User.DoesNotExist:
        return JsonResponse({'code': 404, 'message': '用户不存在', 'data': {}}, status=404)

def register(request):
    data = json.loads(request.body or '{}')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not password or not email:
        return JsonResponse({'code': 400, 'message': '缺少必填字段', 'data': {}}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'code': 409, 'message': '用户名已存在', 'data': {}}, status=409)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'code': 409, 'message': '邮箱已存在', 'data': {}}, status=409)
    u = User.objects.create(username=username, password=make_password(password), email=email)
    return JsonResponse({'code': 200, 'message': '注册成功', 'data': {'id': u.id, 'username': u.username, 'email': u.email}})

def update_user(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    username = request.session.get('user')
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    u = User.objects.filter(username=username).first()
    if not u:
        request.session.flush()
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    data = json.loads(request.body or '{}')
    email = data.get('email')
    password = data.get('password')

    if email:
        u.email = email
    if password:
        u.password = make_password(password)

    u.save()
    return JsonResponse({'code': 200, 'message': '更新成功', 'data': {
        'id': u.id,
        'username': u.username,
        'email': u.email,
    }})


def logout(request):
    request.session.flush()
    return JsonResponse({'code': 200, 'message': 'success', 'data': {}})
