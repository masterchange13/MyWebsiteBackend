import json
import os
import urllib.request
import urllib.error

from django.http import JsonResponse, StreamingHttpResponse
from django.db.models import Max
from django.utils import timezone

from users.models.user_model import User
from agent.models import AgentConversation, AgentMessage
from qi_men_dun_jia.services.deepseek_client import _resolve_api_key


DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')


def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()


def _qs_for_user(u):
    return AgentConversation.objects.filter(user=u)


def _sse(event, data):
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _stream_deepseek(messages, api_key: str):
    key = _resolve_api_key(api_key)
    if not key:
        yield ('error', {'message': 'DeepSeek API key not configured'})
        return

    payload = {
        'model': DEEPSEEK_MODEL,
        'messages': messages,
        'temperature': 0.7,
        'stream': True,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_API_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {key}')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    try:
        with opener.open(req, timeout=180) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                if not line.startswith('data:'):
                    continue
                raw = line[len('data:'):].strip()
                if raw == '[DONE]':
                    yield ('done', {})
                    return
                try:
                    parsed = json.loads(raw)
                except Exception:
                    continue
                choices = parsed.get('choices') or []
                if not choices:
                    continue
                delta = choices[0].get('delta') or {}
                content = delta.get('content')
                if content is None:
                    msg = choices[0].get('message') or {}
                    content = msg.get('content')
                if content:
                    yield ('delta', {'content': content})
    except urllib.error.HTTPError as e:
        yield ('error', {'message': f'HTTP错误: {e.code}'})
    except urllib.error.URLError as e:
        yield ('error', {'message': f'网络错误: {str(e)}'})
    except Exception as e:
        yield ('error', {'message': f'未知错误: {str(e)}'})


def list_conversations(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    qs = _qs_for_user(u).order_by('-update_time')
    data = list(qs.values('id', 'title', 'created_time', 'update_time'))
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})


def create_conversation(request):
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    title = (data.get('title') or '').strip() or '新对话'
    conv = AgentConversation.objects.create(user=u, title=title)
    return JsonResponse({'code': 200, 'message': 'success', 'data': {'id': conv.id, 'title': conv.title}})


def list_messages(request):
    conv_id = request.GET.get('conversation_id') or request.GET.get('id')
    if not conv_id:
        return JsonResponse({'code': 400, 'message': 'conversation_id is required', 'data': []})
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    conv = _qs_for_user(u).filter(id=conv_id).first()
    if not conv:
        return JsonResponse({'code': 404, 'message': 'not found', 'data': []})
    msgs = list(
        conv.messages.order_by('created_time').values('id', 'role', 'content', 'created_time')
    )
    return JsonResponse({'code': 200, 'message': 'success', 'data': {'conversation': {'id': conv.id, 'title': conv.title}, 'messages': msgs}})


def chat_stream(request):
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    conv_id = data.get('conversation_id') or data.get('conversationId')
    user_text = (data.get('message') or data.get('content') or '').strip()
    api_key = data.get('api_key') or ''

    if not user_text:
        return JsonResponse({'code': 400, 'message': 'message is required', 'data': {}}, status=400)

    if conv_id:
        conv = _qs_for_user(u).filter(id=conv_id).first()
    else:
        conv = None

    if not conv:
        conv = AgentConversation.objects.create(user=u, title='新对话')

    AgentMessage.objects.create(conversation=conv, role=AgentMessage.ROLE_USER, content=user_text)

    if conv.title == '新对话':
        conv.title = user_text[:18]
        conv.save(update_fields=['title'])

    conv.update_time = timezone.now()
    conv.save(update_fields=['update_time'])

    history_qs = conv.messages.order_by('created_time')
    max_history = int(data.get('max_history') or 40)
    if max_history > 0:
        max_id = history_qs.aggregate(m=Max('id')).get('m')
        if max_id is not None:
            history_qs = history_qs.filter(id__gte=max_id - max_history * 2)

    system_prompt = (data.get('system') or '').strip() or '你是一个有帮助的中文助手。'
    messages = [{'role': 'system', 'content': system_prompt}]
    for m in history_qs:
        messages.append({'role': m.role, 'content': m.content})

    def gen():
        yield _sse('meta', {'conversation_id': conv.id, 'title': conv.title})
        full = ''
        for ev, payload in _stream_deepseek(messages, api_key):
            if ev == 'delta':
                full += payload.get('content') or ''
                yield _sse('delta', payload)
            elif ev == 'error':
                yield _sse('error', payload)
                return
            elif ev == 'done':
                break
        if full.strip():
            AgentMessage.objects.create(conversation=conv, role=AgentMessage.ROLE_ASSISTANT, content=full)
            conv.update_time = timezone.now()
            conv.save(update_fields=['update_time'])
        yield _sse('done', {})

    resp = StreamingHttpResponse(gen(), content_type='text/event-stream')
    resp['Cache-Control'] = 'no-cache'
    resp['X-Accel-Buffering'] = 'no'
    return resp
