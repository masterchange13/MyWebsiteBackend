import asyncio
import json
import math
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_http_methods

from users.models.user_model import User
from .models import Ebook
from .parser import parse_book
from defusedxml.common import DefusedXmlException


def error(message, status=400):
    return JsonResponse({'code': status, 'message': message, 'data': {}}, status=status)


def current_user(request):
    username = request.session.get('user')
    return User.objects.filter(username=username).first() if username else None


def serialize(book):
    return {
        'id': str(book.id), 'title': book.title, 'author': book.author,
        'format': book.format, 'size': book.size, 'original_name': book.original_name,
        'chapters': book.chapters, 'progress': book.progress,
        'created_at': book.created_at.isoformat(),
        'last_read_at': book.last_read_at.isoformat() if book.last_read_at else None,
    }


@require_http_methods(['GET', 'POST'])
def library(request):
    user = current_user(request)
    if not user:
        return error('请先登录。', 401)
    if request.method == 'GET':
        books = Ebook.objects.filter(user=user)
        query = request.GET.get('q', '').strip()[:100]
        if query:
            books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))
        return JsonResponse({'code': 200, 'data': [serialize(book) for book in books], 'max_upload_mb': settings.EBOOK_MAX_UPLOAD_MB})
    upload = request.FILES.get('file')
    if not upload:
        return error('请选择电子书文件。')
    extension = Path(upload.name).suffix.lower().lstrip('.')
    if extension not in ('txt', 'epub', 'pdf'):
        return error('支持 TXT、EPUB 和 PDF 格式。')
    maximum = settings.EBOOK_MAX_UPLOAD_MB * 1024 * 1024
    if upload.size > maximum:
        return error(f'电子书最大为 {settings.EBOOK_MAX_UPLOAD_MB} MB。', 413)
    data = upload.read(maximum + 1)
    if len(data) > maximum:
        return error('电子书文件过大。', 413)
    try:
        title, author, chapters = parse_book(data, extension)
    except (ValueError, DefusedXmlException):
        return error('文件无法读取：请确认格式有效、未加密，且正文不超过 20 MB。')
    book = Ebook(user=user, format=extension, size=len(data), original_name=upload.name[:255],
        title=(request.POST.get('title', '').strip() or title or Path(upload.name).stem)[:200],
        author=(request.POST.get('author', '').strip() or author)[:200],
        chapters=[{'title': chapter['title'], 'length': len(chapter['text'])} for chapter in chapters])
    try:
        book.file.save(f'original.{extension}', ContentFile(data), save=False)
        if chapters:
            book.content.save('chapters.json', ContentFile(json.dumps(chapters, ensure_ascii=False).encode('utf-8')), save=False)
        book.save()
    except Exception:
        book.file.delete(save=False)
        book.content.delete(save=False)
        raise
    return JsonResponse({'code': 200, 'message': '已加入书架', 'data': serialize(book)})


@require_http_methods(['GET', 'DELETE'])
def detail(request, book_id):
    user = current_user(request)
    if not user:
        return error('请先登录。', 401)
    book = Ebook.objects.filter(id=book_id, user=user).first()
    if not book:
        return error('电子书不存在。', 404)
    if request.method == 'DELETE':
        book.file.delete(save=False)
        book.content.delete(save=False)
        book.delete()
        return JsonResponse({'code': 200, 'message': '已从书架删除', 'data': {}})
    return JsonResponse({'code': 200, 'data': serialize(book)})


@require_http_methods(['GET'])
def chapter(request, book_id, index):
    user = current_user(request)
    if not user:
        return error('请先登录。', 401)
    book = Ebook.objects.filter(id=book_id, user=user).first()
    if not book or not book.content or index >= len(book.chapters):
        return error('章节不存在。', 404)
    try:
        with book.content.open('rb') as source:
            chapters = json.load(source)
        selected = chapters[index]
    except (OSError, ValueError, IndexError):
        return error('章节文件无法读取，请重新上传电子书。', 404)
    return JsonResponse({'code': 200, 'data': selected})


@require_http_methods(['POST'])
def progress(request, book_id):
    user = current_user(request)
    if not user:
        return error('请先登录。', 401)
    book = Ebook.objects.filter(id=book_id, user=user).first()
    if not book:
        return error('电子书不存在。', 404)
    try:
        payload = json.loads(request.body)
        index, page = int(payload.get('chapter', 0)), int(payload.get('page', 1))
        scroll = float(payload.get('scroll', 0))
        font_size = int(payload.get('font_size', 18))
        theme = payload.get('theme', 'sepia')
        if not math.isfinite(scroll) or not 0 <= scroll <= 1 or not 1 <= page <= 100000 or not 14 <= font_size <= 32:
            raise ValueError()
        if theme not in ('light', 'sepia', 'dark') or not 0 <= index < max(1, len(book.chapters)):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        return error('阅读进度无效。')
    book.progress = {'chapter': index, 'page': page, 'scroll': scroll, 'font_size': font_size, 'theme': theme}
    book.last_read_at = timezone.now()
    book.save(update_fields=['progress', 'last_read_at'])
    return JsonResponse({'code': 200, 'data': book.progress})


def chunks(file):
    try:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            yield chunk
    finally:
        file.close()


async def async_chunks(file):
    try:
        while True:
            chunk = await asyncio.to_thread(file.read, 65536)
            if not chunk:
                break
            yield chunk
    finally:
        await asyncio.to_thread(file.close)


@require_http_methods(['GET', 'HEAD'])
def download(request, book_id):
    user = current_user(request)
    if not user:
        return error('请先登录。', 401)
    book = Ebook.objects.filter(id=book_id, user=user).first()
    if not book:
        return error('电子书不存在。', 404)
    try:
        file = book.file.open('rb')
    except OSError:
        return error('电子书文件已丢失。', 404)
    mime = {'pdf': 'application/pdf', 'txt': 'text/plain; charset=utf-8', 'epub': 'application/epub+zip'}[book.format]
    if request.method == 'HEAD':
        file.close()
        response = HttpResponse(content_type=mime)
    else:
        response = StreamingHttpResponse(async_chunks(file) if hasattr(request, 'scope') else chunks(file), content_type=mime)
        response._resource_closers.append(file.close)
    response['Content-Length'] = str(book.size)
    response['Content-Disposition'] = content_disposition_header(True, book.original_name)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
