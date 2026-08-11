import json
import os
import smtplib
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header

from django.http import JsonResponse

from users.models.user_model import User
from emailer.models import SmtpConfig, EmailHistory


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _get_smtp_config(u):
    cfg, _ = SmtpConfig.objects.get_or_create(user=u)
    return cfg


# --- SMTP 配置 ---

def get_smtp_config(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    cfg = _get_smtp_config(u)
    return JsonResponse({
        'code': 200, 'message': 'success',
        'data': {
            'host': cfg.host,
            'port': cfg.port,
            'use_ssl': cfg.use_ssl,
            'username': cfg.username,
            'password': '***' if cfg.password else '',
            'sender_name': cfg.sender_name,
        }
    })


def save_smtp_config(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    data = json.loads(request.body or '{}')
    cfg = _get_smtp_config(u)

    cfg.host = data.get('host', cfg.host)
    cfg.port = int(data.get('port', cfg.port))
    cfg.use_ssl = bool(data.get('use_ssl', cfg.use_ssl))
    cfg.username = data.get('username', cfg.username)
    cfg.sender_name = data.get('sender_name', cfg.sender_name)

    pwd = data.get('password', '')
    if pwd and pwd != '***':
        cfg.password = pwd

    cfg.save()
    return JsonResponse({'code': 200, 'message': 'SMTP 配置已保存', 'data': {}})


# --- 发送邮件 ---

# 常见文件类型 MIME 映射
MIME_MAP = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.zip': 'application/zip',
    '.rar': 'application/vnd.rar',
    '.7z': 'application/x-7z-compressed',
    '.tar': 'application/x-tar',
    '.gz': 'application/gzip',
}


def send_email(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    # multipart/form-data: 表单字段在 request.POST，文件在 request.FILES
    to_email = request.POST.get('to', '').strip()
    subject = request.POST.get('subject', '').strip()
    body = request.POST.get('body', '').strip()

    if not to_email:
        return JsonResponse({'code': 400, 'message': '收件人不能为空', 'data': {}})
    if not subject:
        return JsonResponse({'code': 400, 'message': '主题不能为空', 'data': {}})

    cfg = _get_smtp_config(u)
    if not cfg.username or not cfg.password:
        return JsonResponse({'code': 400, 'message': '请先配置 SMTP 服务器信息', 'data': {}})

    # 文件大小限制
    files = request.FILES.getlist('attachments')
    total_size = sum(f.size for f in files)
    if total_size > 50 * 1024 * 1024:  # 50MB
        return JsonResponse({'code': 400, 'message': '附件总大小超过 50MB 限制', 'data': {}})

    attach_names = []
    temp_files = []
    success = True
    error_msg = ''

    try:
        msg = MIMEMultipart()
        sender_name = cfg.sender_name or cfg.username
        msg['From'] = f'{sender_name} <{cfg.username}>'
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')

        if body:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 附加文件
        for upload in files:
            filename = upload.name
            attach_names.append(filename)

            # 确定 MIME 类型
            _, ext = os.path.splitext(filename)
            mime_type = MIME_MAP.get(ext.lower(), 'application/octet-stream')
            main_type, sub_type = mime_type.split('/', 1)

            part = MIMEBase(main_type, sub_type)
            content = upload.read()
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename=('utf-8', '', filename),
            )
            msg.attach(part)

        if cfg.use_ssl:
            server = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30)
        else:
            server = smtplib.SMTP(cfg.host, cfg.port, timeout=30)

        server.login(cfg.username, cfg.password)
        server.sendmail(cfg.username, [a.strip() for a in to_email.split(',')], msg.as_string())
        server.quit()
    except Exception as e:
        success = False
        error_msg = str(e)
    finally:
        # 清理临时文件（如果有的话）
        for fp in temp_files:
            try:
                os.unlink(fp)
            except OSError:
                pass

    # 记录历史
    attach_info = f'附件({len(attach_names)}): ' + ', '.join(attach_names) if attach_names else ''
    EmailHistory.objects.create(
        user=u,
        to_email=to_email,
        subject=subject,
        body=(body[:2000] + '\n' + attach_info).strip(),
        success=success,
        error_msg=error_msg[:500],
    )

    if success:
        return JsonResponse({'code': 200, 'message': '发送成功', 'data': {'files': len(attach_names)}})
    else:
        return JsonResponse({'code': 500, 'message': f'发送失败: {error_msg}', 'data': {}})


# --- 发送历史 ---

def get_history(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)

    limit = int(request.GET.get('limit', 30))
    limit = max(1, min(limit, 100))

    qs = EmailHistory.objects.filter(user=u).order_by('-created_at')[:limit]
    data = list(qs.values('id', 'to_email', 'subject', 'success', 'error_msg', 'created_at'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def delete_history(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    ids = json.loads(request.body or '{}').get('ids', [])
    if ids:
        EmailHistory.objects.filter(user=u, id__in=ids).delete()
    else:
        EmailHistory.objects.filter(user=u).delete()

    return JsonResponse({'code': 200, 'message': '已删除', 'data': {}})
