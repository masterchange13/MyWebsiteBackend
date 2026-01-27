import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

def test(request):
    return HttpResponse('<h1> hello test')

def login(request):
    data = json.loads(request.body)

    username = data.get('username')
    password = data.get('password')

    if username == 'admin' and password == 'admin':
        request.session['user'] = username   # 建立 session
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'msg': '用户名或密码错误'}, status=400)
