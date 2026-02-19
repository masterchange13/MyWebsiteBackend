import json
from django.http import JsonResponse, HttpResponse
from document.models.document_model import Document

def publish(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # 处理数据
        # ...
        author = data.get('author')
        content = data.get('content')
        # 保存数据到数据库
        Document.objects.create(author=author, content=content)
        return JsonResponse({'code': 200, 'message': 'Document published successfully', 'data': {}})
    else:
        return HttpResponse(status=405)  # Method Not Allowed
    
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
