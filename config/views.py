from django.shortcuts import render

# Create your views here.
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json

from config.models import Feedback, WebsiteSetting
from users.models.user_model import User

DEFAULT_TOP_LEVEL_ORDER = ['media', 'tools', 'chat', 'navigator', 'blog', 'guide', 'feedback', 'author', 'siteSettings']
DEFAULT_SUBMENU_ORDERS = {
    'media': ['video', 'document', 'music', 'transfer', 'todoList'],
    'tools': ['agent', 'qiMen', 'timer', 'calculator'],
}
DEFAULT_WEBSITE_SETTINGS = {
    'site_title': 'Raspberrypi Console',
    'login_title': '欢迎回来',
    'login_slogan': '快速进入你的个人聚合空间',
    'theme': 'cyber',
    'density': 'balanced',
    'surface_style': 'glass',
    'corner_style': 'soft',
    'font_scale': 'normal',
    'show_petals': True,
    'top_level_order': DEFAULT_TOP_LEVEL_ORDER,
    'submenu_orders': DEFAULT_SUBMENU_ORDERS,
}

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'code': 200, 'message': 'CSRF cookie set', 'data': {}})

def _get_request_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()


def _normalize_order(value, default):
    items = value if isinstance(value, list) else default
    clean = []
    for item in items:
        if isinstance(item, str) and item in default and item not in clean:
            clean.append(item)
    for item in default:
        if item not in clean:
            clean.append(item)
    return clean


def _normalize_settings_payload(data):
    payload = dict(DEFAULT_WEBSITE_SETTINGS)
    payload['site_title'] = str(data.get('site_title') or DEFAULT_WEBSITE_SETTINGS['site_title']).strip()[:120] or DEFAULT_WEBSITE_SETTINGS['site_title']
    payload['login_title'] = str(data.get('login_title') or DEFAULT_WEBSITE_SETTINGS['login_title']).strip()[:120] or DEFAULT_WEBSITE_SETTINGS['login_title']
    payload['login_slogan'] = str(data.get('login_slogan') or DEFAULT_WEBSITE_SETTINGS['login_slogan']).strip()[:255] or DEFAULT_WEBSITE_SETTINGS['login_slogan']
    payload['theme'] = str(data.get('theme') or DEFAULT_WEBSITE_SETTINGS['theme']).strip()[:50] or DEFAULT_WEBSITE_SETTINGS['theme']
    payload['density'] = str(data.get('density') or DEFAULT_WEBSITE_SETTINGS['density']).strip()[:50] or DEFAULT_WEBSITE_SETTINGS['density']
    payload['surface_style'] = str(data.get('surface_style') or DEFAULT_WEBSITE_SETTINGS['surface_style']).strip()[:50] or DEFAULT_WEBSITE_SETTINGS['surface_style']
    payload['corner_style'] = str(data.get('corner_style') or DEFAULT_WEBSITE_SETTINGS['corner_style']).strip()[:50] or DEFAULT_WEBSITE_SETTINGS['corner_style']
    payload['font_scale'] = str(data.get('font_scale') or DEFAULT_WEBSITE_SETTINGS['font_scale']).strip()[:50] or DEFAULT_WEBSITE_SETTINGS['font_scale']
    payload['show_petals'] = bool(data.get('show_petals', DEFAULT_WEBSITE_SETTINGS['show_petals']))
    payload['top_level_order'] = _normalize_order(data.get('top_level_order'), DEFAULT_TOP_LEVEL_ORDER)
    submenu_orders = data.get('submenu_orders') if isinstance(data.get('submenu_orders'), dict) else {}
    payload['submenu_orders'] = {
        'media': _normalize_order(submenu_orders.get('media'), DEFAULT_SUBMENU_ORDERS['media']),
        'tools': _normalize_order(submenu_orders.get('tools'), DEFAULT_SUBMENU_ORDERS['tools']),
    }
    return payload


def _serialize_website_settings(setting=None):
    if not setting:
        return dict(DEFAULT_WEBSITE_SETTINGS)
    return {
        'site_title': setting.site_title,
        'login_title': setting.login_title,
        'login_slogan': setting.login_slogan,
        'theme': setting.theme,
        'density': setting.density,
        'surface_style': setting.surface_style,
        'corner_style': setting.corner_style,
        'font_scale': setting.font_scale,
        'show_petals': setting.show_petals,
        'top_level_order': setting.top_level_order or list(DEFAULT_TOP_LEVEL_ORDER),
        'submenu_orders': setting.submenu_orders or dict(DEFAULT_SUBMENU_ORDERS),
    }


@require_http_methods(["GET"])
def get_website_settings(_request):
    setting = WebsiteSetting.objects.filter(key='default').first()
    return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_website_settings(setting)})


@require_http_methods(["POST"])
def save_website_settings(request):
    if not _get_request_user(request):
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)

    data = json.loads(request.body or '{}')
    payload = _normalize_settings_payload(data)
    setting, _created = WebsiteSetting.objects.get_or_create(key='default')
    setting.site_title = payload['site_title']
    setting.login_title = payload['login_title']
    setting.login_slogan = payload['login_slogan']
    setting.theme = payload['theme']
    setting.density = payload['density']
    setting.surface_style = payload['surface_style']
    setting.corner_style = payload['corner_style']
    setting.font_scale = payload['font_scale']
    setting.show_petals = payload['show_petals']
    setting.top_level_order = payload['top_level_order']
    setting.submenu_orders = payload['submenu_orders']
    setting.save(update_fields=[
        'site_title',
        'login_title',
        'login_slogan',
        'theme',
        'density',
        'surface_style',
        'corner_style',
        'font_scale',
        'show_petals',
        'top_level_order',
        'submenu_orders',
        'update_time',
    ])
    return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_website_settings(setting)})

@require_http_methods(["POST"])
def submit_feedback(request):
    data = json.loads(request.body or '{}')
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    contact = (data.get('contact') or '').strip()
    if not title:
        return JsonResponse({'code': 400, 'message': 'title is required', 'data': {}})
    if not content:
        return JsonResponse({'code': 400, 'message': 'content is required', 'data': {}})

    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': {}}, status=401)
    fb = Feedback.objects.create(
        user=u,
        title=title,
        content=content,
        contact=contact,
    )
    return JsonResponse({'code': 200, 'message': 'success', 'data': {'id': fb.id}})

@require_http_methods(["GET"])
def list_feedback(request):
    u = _get_request_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '未登录', 'data': []}, status=401)
    qs = Feedback.objects.select_related('user').all().order_by('-created_time')

    data = []
    for fb in qs[:200]:
        data.append({
            'id': fb.id,
            'title': fb.title,
            'content': fb.content,
            'contact': fb.contact,
            'status': fb.status,
            'reply': fb.reply,
            'username': fb.user.username if fb.user else None,
            'created_time': fb.created_time,
            'update_time': fb.update_time,
        })
    return JsonResponse({'code': 200, 'message': 'success', 'data': data})
