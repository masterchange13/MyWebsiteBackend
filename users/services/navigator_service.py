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