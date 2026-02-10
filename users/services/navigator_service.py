from django.http import JsonResponse
from users.models.navigator_model import Navigator
import json
from django.http import JsonResponse
from users.models.navigator_model import Navigator

def get_all_navigators(request):
    data = list(
        Navigator.objects.values('id', 'name', 'img', 'url')
    )
    return JsonResponse({'data': data})

def save_icon(request):
    data = json.loads(request.body)   # ⭐ 关键

    print('data is', data)

    Navigator.objects.create(
        name=data.get('name'),
        img=data.get('img'),
        url=data.get('url')
    )

    return JsonResponse({'code': 200, 'data': 'Icon saved successfully'})

def remove_icon(request):
    try:
        raw = request.body or b''
        data = json.loads(raw.decode('utf-8')) if raw else {}
    except Exception as e:
        data = {}
    navigator_id = data.get('id') or request.GET.get('id')
    if not navigator_id:
        return JsonResponse({'code': 400, 'message': 'id is required'})
    Navigator.objects.filter(id=navigator_id).delete()
    return JsonResponse({'code': 200, 'data': 'Icon removed successfully'})
