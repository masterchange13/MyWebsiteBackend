import os
import mimetypes
from pathlib import Path

from django.http import JsonResponse, FileResponse

# Extensions that should be displayed inline as plain text in the browser
# (otherwise text/csv etc. trigger downloads even with Content-Disposition: inline)
_TEXT_EXTENSIONS = {
    'csv', 'tsv', 'txt', 'log', 'md', 'rst',
    'py', 'js', 'ts', 'jsx', 'tsx', 'vue', 'svelte',
    'html', 'htm', 'css', 'scss', 'less', 'sass',
    'json', 'xml', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf',
    'sh', 'bash', 'zsh', 'fish', 'bat', 'ps1',
    'sql', 'graphql', 'gql',
    'java', 'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'rs', 'go', 'rb', 'php',
    'swift', 'kt', 'scala', 'r', 'pl', 'lua', 'dart',
    'makefile', 'cmake', 'dockerfile',
    'env', 'gitignore', 'editorconfig',
}


def _get_ext(filename: str) -> str:
    """Return lowercase extension without the dot, or empty string."""
    name = (filename or '').lower()
    if '.' not in name:
        return ''
    return name.rsplit('.', 1)[-1]


def _base_dir():
    return Path(__file__).resolve().parents[2]


def _get_username(request):
    return request.session.get('user')


def _safe_part(s):
    s = (s or '').strip()
    if not s:
        return 'public'
    s = s.replace('\\', '/').split('/')[-1]
    allowed = []
    for ch in s:
        if ch.isalnum() or ch in ('-', '_', '.'):
            allowed.append(ch)
    res = ''.join(allowed).strip('._')
    return res or 'public'


def _uploads_dir(username):
    base = _base_dir()
    target = base / 'media' / 'file' / 'uploads' / _safe_part(username)
    os.makedirs(target, exist_ok=True)
    return target


def _unique_path(dir_path: Path, filename: str):
    name = _safe_part(filename)
    if not name:
        name = 'file'
    candidate = dir_path / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    i = 1
    while True:
        cand = dir_path / f'{stem}_{i}{suffix}'
        if not cand.exists():
            return cand
        i += 1


def upload(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'method not allowed', 'data': {}})

    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'code': 400, 'message': 'file is required', 'data': {}})

    username = _get_username(request)
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    target_dir = _uploads_dir(username)
    target_path = _unique_path(target_dir, f.name)

    with open(target_path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)

    url = f'/api/file/open/{target_path.name}'
    return JsonResponse(
        {
            'code': 200,
            'message': '上传成功',
            'data': {
                'name': target_path.name,
                'url': url,
            },
        }
    )


def list_files(request):
    username = _get_username(request)
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    target_dir = _uploads_dir(username)
    files = []
    for entry in os.scandir(target_dir):
        if not entry.is_file():
            continue
        stat = entry.stat()
        files.append(
            {
                'name': entry.name,
                'size': stat.st_size,
                'mtime': int(stat.st_mtime),
                'url': f'/api/file/open/{entry.name}',
            }
        )
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return JsonResponse({'code': 200, 'message': 'success', 'data': files})


def open_file(request, filename):
    username = _get_username(request)
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    target_dir = _uploads_dir(username)
    safe_name = _safe_part(filename)
    file_path = (target_dir / safe_name).resolve()
    if target_dir.resolve() not in file_path.parents:
        return JsonResponse({'code': 400, 'message': 'invalid filename', 'data': {}})
    if not file_path.exists() or not file_path.is_file():
        return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

    content_type, _ = mimetypes.guess_type(str(file_path))
    content_type = content_type or 'application/octet-stream'

    # Force text-based files (csv, code, etc.) to text/plain so browsers
    # display them inline instead of triggering a download.
    ext = _get_ext(safe_name)
    if ext in _TEXT_EXTENSIONS:
        content_type = 'text/plain; charset=utf-8'

    resp = FileResponse(open(file_path, 'rb'), content_type=content_type)
    resp['Content-Disposition'] = f'inline; filename="{safe_name}"'
    return resp


def download_file(request, filename):
    """Serve a file as an attachment (always triggers download)."""
    username = _get_username(request)
    if not username:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    target_dir = _uploads_dir(username)
    safe_name = _safe_part(filename)
    file_path = (target_dir / safe_name).resolve()
    if target_dir.resolve() not in file_path.parents:
        return JsonResponse({'code': 400, 'message': 'invalid filename', 'data': {}})
    if not file_path.exists() or not file_path.is_file():
        return JsonResponse({'code': 404, 'message': 'not found', 'data': {}})

    content_type, _ = mimetypes.guess_type(str(file_path))
    content_type = content_type or 'application/octet-stream'
    resp = FileResponse(open(file_path, 'rb'), content_type=content_type)
    resp['Content-Disposition'] = f'attachment; filename="{safe_name}"'
    return resp
