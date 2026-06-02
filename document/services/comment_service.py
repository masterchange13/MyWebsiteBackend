import json
from django.http import JsonResponse, HttpResponse
from document.models.comment_model import Comment
from document.models.document_model import Document
from users.models.user_model import User


def _get_session_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()


def add_comment(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    data = json.loads(request.body or '{}')
    document_id = data.get('document_id')
    author = data.get('author', '').strip()
    content = data.get('content', '').strip()

    if not document_id or not author or not content:
        return JsonResponse({'code': 400, 'message': 'document_id, author and content are required', 'data': {}}, status=400)

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

    comment = Comment.objects.create(
        document=doc,
        author=author,
        content=content,
    )

    return JsonResponse({
        'code': 200,
        'message': 'Comment added',
        'data': {
            'id': comment.id,
            'author': comment.author,
            'content': comment.content,
            'created_time': comment.created_time.isoformat(),
        }
    })


def get_comments(request):
    document_id = request.GET.get('document_id')
    if not document_id:
        return JsonResponse({'code': 400, 'message': 'document_id is required', 'data': {}}, status=400)

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Document not found', 'data': {}}, status=404)

    comments = doc.comments.all()
    data = [{
        'id': c.id,
        'author': c.author,
        'content': c.content,
        'created_time': c.created_time.isoformat(),
    } for c in comments]

    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def delete_comment(request, comment_id):
    if request.method != 'DELETE':
        return HttpResponse(status=405)

    session_user = _get_session_user(request)
    username = request.session.get('user')

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Comment not found', 'data': {}}, status=404)

    # Only the comment author can delete
    is_author = (
        (session_user and comment.author == session_user.username) or
        (username and comment.author == username)
    )
    if not is_author:
        return JsonResponse({'code': 403, 'message': '只能删除自己的评论', 'data': {}}, status=403)

    comment.delete()
    return JsonResponse({'code': 200, 'message': 'Comment deleted', 'data': {}})
