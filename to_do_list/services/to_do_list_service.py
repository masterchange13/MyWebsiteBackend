import json
from django.http import JsonResponse, HttpResponse
from to_do_list.models.to_do_list_model import ToDoList
from django.shortcuts import get_object_or_404

# path('todo/list', views.get_to_do_list),
# path('todo/add', views.add_to_do_list),
# path('todo/update', views.update_to_do_list),
# path('todo/remove', views.remove_to_do_list),
# path('todo/getAll', views.get_all_to_do_list),
# path('todo/updateTodoStatus', views.update_to_do_status),
# path('todo/doneEdit', views.done_edit),
# path('todo/removeCompleted', views.remove_completed),
def get_to_do_list(request):
    to_do_list = ToDoList.objects.all()
    to_do_list_data = []
    for todo in to_do_list:
        to_do_list_data.append({
            'id': todo.id,
            'title': todo.title,
            'completed': todo.completed,
            'due_date': todo.due_date
        })

    return JsonResponse({'code': 200, 'message': 'To do list retrieved successfully', 'data': to_do_list_data})


def add_to_do_list(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        title = data.get('title')
        completed = data.get('completed', False)  # 给默认值更安全

        # ✅ 保存到数据库
        to_do_list = ToDoList.objects.create(
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

    return JsonResponse({'code': 400, 'message': 'Invalid request method'})
    
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
            return JsonResponse({'code': 400, 'message': 'id is required'})

        obj = get_object_or_404(ToDoList, id=todo_id)
        obj.delete()

        return JsonResponse({'code': 200, 'message': 'To do list removed successfully'})

    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)})
    
def get_all_to_do_list(request):
    data = list(ToDoList.objects.all().values())
    return JsonResponse({'code': 200, 'message': 'To do list retrieved successfully', 'data': data})

def update_to_do_status(request):
    data = json.loads(request.body)

    id = data.get('id')
    completed = data.get('completed')

    obj = ToDoList.objects.get(id=id)
    obj.completed = completed
    obj.save()

    return JsonResponse({'code': 200, 'message': 'To do list updated successfully', 'data': {'id': obj.id,}})

def done_edit(request):
    data = json.loads(request.body)

    id = data.get('id')
    title = data.get('title')

    obj = ToDoList.objects.get(id=id)
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
    ToDoList.objects.filter(completed=True).delete()
    return JsonResponse({'code': 200, 'message': 'Completed to do list removed successfully'})