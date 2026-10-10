"""Local audio delivery with byte ranges for browser seeking."""
import asyncio
import mimetypes
import os
import re

from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import http_date, parse_http_date_safe
from django.views.decorators.http import require_safe

from music.models.music_model import Music

CHUNK_SIZE = 64 * 1024


class UnsatisfiableRange(ValueError):
    pass


def byte_range(header, size):
    # Unsupported units, malformed headers and multiple ranges are ignored.
    # Browser audio seeks use a single range.
    if len(header) > 128:
        return None
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
    if not match or not any(match.groups()):
        return None
    first, last = match.groups()
    if not first:
        suffix = int(last)
        if suffix <= 0 or size == 0:
            raise UnsatisfiableRange()
        return max(0, size - suffix), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        raise UnsatisfiableRange()
    return start, end


def file_chunks(file, start, length):
    try:
        file.seek(start)
        remaining = length
        while remaining:
            chunk = file.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        file.close()


async def async_file_chunks(file, start, length):
    try:
        await asyncio.to_thread(file.seek, start)
        remaining = length
        while remaining:
            chunk = await asyncio.to_thread(file.read, min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        await asyncio.to_thread(file.close)


@require_safe
def audio_response(request, filename):
    if filename in ('.', '..') or '/' in filename or '\\' in filename:
        raise Http404('音频不存在')
    storage = Music._meta.get_field('audio').storage
    try:
        file = open(storage.path(f'media/music/audio/{filename}'), 'rb')
    except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
        raise Http404('音频不存在') from error
    stat = os.fstat(file.fileno())
    size = stat.st_size
    etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
    header = request.headers.get('Range', '') if request.method == 'GET' else ''
    if_range = request.headers.get('If-Range')
    if if_range:
        timestamp = parse_http_date_safe(if_range)
        if if_range != etag and (timestamp is None or timestamp < int(stat.st_mtime)):
            header = ''
    try:
        selected = byte_range(header, size)
    except UnsatisfiableRange:
        file.close()
        response = HttpResponse(status=416)
        response['Content-Range'] = f'bytes */{size}'
        response['Content-Length'] = '0'
    else:
        start, end = selected if selected else (0, size - 1)
        length = max(0, end - start + 1)
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        if request.method == 'HEAD':
            file.close()
            response = HttpResponse(content_type=content_type)
        else:
            chunks = async_file_chunks if hasattr(request, 'scope') else file_chunks
            response = StreamingHttpResponse(
                chunks(file, start, length), status=206 if selected else 200,
                content_type=content_type,
            )
            # Also close a file if Django closes the response before iteration.
            response._resource_closers.append(file.close)
        response['Content-Length'] = str(length)
        if selected:
            response['Content-Range'] = f'bytes {start}-{end}/{size}'
    response['Accept-Ranges'] = 'bytes'
    response['ETag'] = etag
    response['Last-Modified'] = http_date(stat.st_mtime)
    response['Cache-Control'] = 'no-transform'
    return response
