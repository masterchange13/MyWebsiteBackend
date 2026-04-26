import json
from django.http import JsonResponse, HttpResponse
from document.models.document_model import Document

def publish(request):
    if request.method != 'POST':
        return HttpResponse(status=405)  # Method Not Allowed

    data = json.loads(request.body or '{}')
    document_id = data.get('id') or data.get('document_id')
    print('document_id is ', document_id)
    author = data.get('author')
    title = data.get('title')
    content = data.get('content')

    if not title or not content:
        return JsonResponse({'code': 400, 'message': 'title and content are required', 'data': {}}, status=400)

    if document_id:
        try:
            doc = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

        doc.author = author if author is not None else doc.author
        doc.title = title
        doc.content = content
        doc.save(update_fields=['author', 'title', 'content', 'update_time'])
        return JsonResponse({'code': 200, 'message': 'Document updated successfully', 'data': {'id': doc.id}})

    doc = Document.objects.create(author=author or '', title=title, content=content)
    return JsonResponse({'code': 200, 'message': 'Document published successfully', 'data': {'id': doc.id}})
    
def get_all(request):
    if request.method == 'GET':
        documents = Document.objects.all()

        data = []
        for doc in documents:
            data.append({
                'id': doc.id,
                'author': doc.author,
                'title': doc.title,
                'content': doc.content,
                'created_time': doc.created_time,
                'update_time': doc.update_time
            })

        return JsonResponse({
            'code': 200,
            'message': 'Documents retrieved successfully',
            'data': data
        })

def detail(request, document_id=None):
    # if request.method != 'GET':
        # return HttpResponse(status=405)

    document_id = document_id or request.GET.get('document_id') or request.GET.get('id')
    print('document_id is ', document_id)
    if not document_id:
        return JsonResponse({'code': 400, 'message': 'document_id is required', 'data': {}}, status=400)

    try:
        doc = Document.objects.select_related('user').get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

    data = {
        'id': doc.id,
        'author': doc.author,
        'title': doc.title,
        'content': doc.content,
        'created_time': doc.created_time,
        'update_time': doc.update_time,
    }
    if doc.user_id:
        data['user'] = {'id': doc.user_id, 'username': doc.user.username}

    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def remove(request, document_id):
    if request.method != 'DELETE':
        return HttpResponse(status=405)
    if not document_id:
        return JsonResponse({'code': 400, 'message': 'document_id is required', 'data': {}}, status=400)

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

    doc.delete()
    return JsonResponse({'code': 200, 'message': 'Document removed successfully', 'data': {'id': int(document_id)}})
