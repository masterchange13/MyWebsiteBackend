import json
from django.http import JsonResponse, HttpResponse
from to_do_list.models.to_do_list_model import ToDoList
from django.shortcuts import get_object_or_404
from users.models.user_model import User

# path('todo/list', views.get_to_do_list),
# path('todo/add', views.add_to_do_list),
# path('todo/update', views.update_to_do_list),
# path('todo/remove', views.remove_to_do_list),
# path('todo/getAll', views.get_all_to_do_list),
# path('todo/updateTodoStatus', views.update_to_do_status),
# path('todo/doneEdit', views.done_edit),
# path('todo/removeCompleted', views.remove_completed),
def _get_request_user(request):
    username = request.session.get('user') or request.GET.get('username') or request.POST.get('username')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

def get_to_do_list(request):
    u = _get_request_user(request)
    qs = ToDoList.objects.all()
    if u:
        qs = qs.filter(user=u)
    to_do_list = qs
    to_do_list_data = []
    for todo in to_do_list:
        to_do_list_data.append({
            'id': todo.id,
            'title': todo.title,
            'completed': todo.completed,
            'created_time': todo.created_time,
            'updated_time': todo.updated_time,
        })

    return JsonResponse({'code': 200, 'message': 'To do list retrieved successfully', 'data': to_do_list_data})


def add_to_do_list(request):
    if request.method == 'POST':
        data = json.loads(request.body or '{}')

        title = data.get('title')
        completed = data.get('completed', False)  # 给默认值更安全

        # ✅ 保存到数据库
        u = _get_request_user(request)
        to_do_list = ToDoList.objects.create(
            user=u,
            title=title,
            completed=completed
        )

        return JsonResponse({
            'code': 200,
            'message': 'To do list added successfully',
            'data': {
                # 'id': to_do_list.id,
                'title': to_do_list.title,
                'completed': to_do_list.completed
            }
        })

    return JsonResponse({'code': 400, 'message': 'Invalid request method', 'data': {}})
    
def update_to_do_list(request):
    return 

def remove_to_do_list(request):
    if request.method != 'DELETE':
        return JsonResponse({'code': 400, 'message': 'Invalid request method'})

    try:
        data = json.loads(request.body or '{}')
        print('delete data is ', data)
        todo_id = data.get('id')
        if not todo_id:
            return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}})

        u = _get_request_user(request)
        if u:
            obj = get_object_or_404(ToDoList, id=todo_id, user=u)
        else:
            obj = get_object_or_404(ToDoList, id=todo_id)
        obj.delete()

        return JsonResponse({'code': 200, 'message': 'To do list removed successfully', 'data': {}})

    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e), 'data': {}})
    
def get_all_to_do_list(request):
    u = _get_request_user(request)
    qs = ToDoList.objects.all()
    if u:
        qs = qs.filter(user=u)
    data = list(qs.values())
    return JsonResponse({'code': 200, 'message': 'To do list retrieved successfully', 'data': data})

def update_to_do_status(request):
    data = json.loads(request.body or '{}')

    id = data.get('id')
    completed = data.get('completed')

    u = _get_request_user(request)
    if u:
        obj = get_object_or_404(ToDoList, id=id, user=u)
    else:
        obj = get_object_or_404(ToDoList, id=id)
    obj.completed = completed
    obj.save()

    return JsonResponse({'code': 200, 'message': 'To do list updated successfully', 'data': {'id': obj.id,}})

def done_edit(request):
    data = json.loads(request.body or '{}')

    id = data.get('id')
    title = data.get('title')

    u = _get_request_user(request)
    if u:
        obj = get_object_or_404(ToDoList, id=id, user=u)
    else:
        obj = get_object_or_404(ToDoList, id=id)
    obj.title = title
    obj.save()

    return JsonResponse({
        'code': 200,
        'message': 'To do list updated successfully',
        'data': {
            'id': obj.id,
            'title': obj.title,
            'completed': obj.completed
        }
    })

def remove_completed(request):
    u = _get_request_user(request)
    qs = ToDoList.objects.filter(completed=True)
    if u:
        qs = qs.filter(user=u)
    qs.delete()
    return JsonResponse({'code': 200, 'message': 'Completed to do list removed successfully', 'data': {}})
