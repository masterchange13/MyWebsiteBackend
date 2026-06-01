import json
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from document.models.document_model import Document
from users.models.user_model import User

def _get_session_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()

def _is_owner(doc, username=None, user_obj=None):
    if user_obj and doc.user_id and doc.user_id == user_obj.id:
        return True
    if username and doc.author and doc.author == username:
        return True
    return False

def publish(request):
    if request.method != 'POST':
        return HttpResponse(status=405)  # Method Not Allowed

    data = json.loads(request.body or '{}')
    document_id = data.get('id') or data.get('document_id')
    print('document_id is ', document_id)
    author = data.get('author')
    title = data.get('title')
    content = data.get('content')
    is_public = bool(data.get('is_public', True))
    session_user = _get_session_user(request)

    if not title or not content:
        return JsonResponse({'code': 400, 'message': 'title and content are required', 'data': {}}, status=400)

    if document_id:
        try:
            doc = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

        if not _is_owner(doc, request.session.get('user'), session_user):
            return JsonResponse({'code': 403, 'message': '只有作者可以修改这篇文章', 'data': {}}, status=403)

        doc.author = author if author is not None else doc.author
        doc.title = title
        doc.content = content
        doc.is_public = is_public
        if session_user and not doc.user_id:
            doc.user = session_user
        doc.save(update_fields=['author', 'title', 'content', 'is_public', 'user', 'update_time'])
        return JsonResponse({'code': 200, 'message': 'Document updated successfully', 'data': {'id': doc.id}})

    doc = Document.objects.create(
        author=author or '',
        title=title,
        content=content,
        is_public=is_public,
        user=session_user,
    )
    return JsonResponse({'code': 200, 'message': 'Document published successfully', 'data': {'id': doc.id}})
    
def get_all(request):
    if request.method == 'GET':
        session_user = _get_session_user(request)
        documents = Document.objects.select_related('user').order_by('-update_time')
        if session_user:
            documents = documents.filter(Q(is_public=True) | Q(user=session_user))
        else:
            documents = documents.filter(is_public=True)
        documents = documents.order_by('-update_time')

        data = []
        for doc in documents:
            data.append({
                'id': doc.id,
                'author': doc.author,
                'title': doc.title,
                'content': doc.content,
                'is_public': doc.is_public,
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

    session_user = _get_session_user(request)
    username = request.session.get('user')
    if not doc.is_public and not _is_owner(doc, username, session_user):
        return JsonResponse({'code': 403, 'message': '该文章仅作者可见', 'data': {}}, status=403)

    data = {
        'id': doc.id,
        'author': doc.author,
        'title': doc.title,
        'content': doc.content,
        'is_public': doc.is_public,
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

    session_user = _get_session_user(request)
    username = request.session.get('user')
    if not _is_owner(doc, username, session_user):
        return JsonResponse({'code': 403, 'message': '只有作者可以删除这篇文章', 'data': {}}, status=403)

    doc.delete()
    return JsonResponse({'code': 200, 'message': 'Document removed successfully', 'data': {'id': int(document_id)}})
