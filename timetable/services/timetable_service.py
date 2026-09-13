import json
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from timetable.models.timetable_model import TimetableEntry
from timetable.models.timetable_config_model import TimetableConfig
from users.models.user_model import User

DEFAULT_PERIODS = [
    {'n': 1, 'start': '08:00', 'end': '08:40'},
    {'n': 2, 'start': '08:45', 'end': '09:25'},
    {'n': 3, 'start': '09:45', 'end': '10:25'},
    {'n': 4, 'start': '10:35', 'end': '11:15'},
    {'n': 5, 'start': '11:20', 'end': '12:00'},
    {'n': 6, 'start': '13:30', 'end': '14:10'},
    {'n': 7, 'start': '14:15', 'end': '14:55'},
    {'n': 8, 'start': '15:15', 'end': '15:55'},
    {'n': 9, 'start': '16:00', 'end': '16:40'},
    {'n': 10, 'start': '18:30', 'end': '19:10'},
    {'n': 11, 'start': '19:15', 'end': '19:55'},
    {'n': 12, 'start': '20:05', 'end': '20:45'},
]

DEFAULT_COLOR = '#00f5ff'
MAX_PERIODS = 20
MAX_WEEK = 25
TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


def _get_session_user(request):
    username = request.session.get('user')
    if not username:
        return None
    return User.objects.filter(username=username).first()


def _require_user(request):
    u = _get_session_user(request)
    if not u:
        return JsonResponse({'code': 401, 'message': '请先登录', 'data': {}}, status=401)
    return u


def _serialize(entry):
    return {
        'id': entry.id,
        'name': entry.name,
        'teacher': entry.teacher,
        'location': entry.location,
        'day_of_week': entry.day_of_week,
        'start_period': entry.start_period,
        'end_period': entry.end_period,
        'week_start': entry.week_start,
        'week_end': entry.week_end,
        'week_type': entry.week_type,
        'color': entry.color,
        'created_time': entry.created_time,
        'updated_time': entry.updated_time,
    }


def _validate_payload(data):
    """返回 (cleaned_fields, error_message)。合法时 error 为 None。"""
    name = (data.get('name') or '').strip()
    location = (data.get('location') or '').strip()
    if not name:
        return None, '课程名称不能为空'
    if not location:
        return None, '上课地点不能为空'

    try:
        day_of_week = int(data.get('day_of_week'))
        start_period = int(data.get('start_period'))
        end_period = int(data.get('end_period'))
    except (TypeError, ValueError):
        return None, '星期/节次必须是数字'

    if not (1 <= day_of_week <= 7):
        return None, '星期必须在 1~7 之间'
    if start_period < 1:
        return None, '开始节次必须 >= 1'
    if end_period < start_period:
        return None, '结束节次不能小于开始节次'

    week_start = data.get('week_start', 1)
    week_end = data.get('week_end', 16)
    try:
        week_start = int(week_start)
        week_end = int(week_end)
    except (TypeError, ValueError):
        return None, '周次必须是数字'
    if not (1 <= week_start <= MAX_WEEK and 1 <= week_end <= MAX_WEEK):
        return None, f'周次必须在 1~{MAX_WEEK} 之间'
    if week_end < week_start:
        return None, '结束周不能小于起始周'

    week_type = data.get('week_type', 'all')
    if week_type not in ('all', 'odd', 'even'):
        return None, 'week_type 不合法'

    color = data.get('color') or DEFAULT_COLOR
    if not COLOR_RE.match(str(color)):
        color = DEFAULT_COLOR

    cleaned = {
        'name': name,
        'teacher': (data.get('teacher') or '').strip(),
        'location': location,
        'day_of_week': day_of_week,
        'start_period': start_period,
        'end_period': end_period,
        'week_start': week_start,
        'week_end': week_end,
        'week_type': week_type,
        'color': color,
    }
    return cleaned, None


def get_list(request):
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    entries = TimetableEntry.objects.filter(user=u)
    data = [_serialize(e) for e in entries]
    return JsonResponse({'code': 200, 'message': 'Timetable retrieved successfully', 'data': data})


def add_entry(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    data = json.loads(request.body or '{}')
    cleaned, err = _validate_payload(data)
    if err:
        return JsonResponse({'code': 400, 'message': err, 'data': {}}, status=400)

    entry = TimetableEntry.objects.create(user=u, **cleaned)
    return JsonResponse({'code': 200, 'message': 'Course added successfully', 'data': _serialize(entry)})


def update_entry(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    data = json.loads(request.body or '{}')
    entry_id = data.get('id')
    if not entry_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}}, status=400)

    entry = get_object_or_404(TimetableEntry, id=entry_id, user=u)
    cleaned, err = _validate_payload(data)
    if err:
        return JsonResponse({'code': 400, 'message': err, 'data': {}}, status=400)

    for field, value in cleaned.items():
        setattr(entry, field, value)
    entry.save(update_fields=list(cleaned.keys()) + ['updated_time'])
    return JsonResponse({'code': 200, 'message': 'Course updated successfully', 'data': _serialize(entry)})


def remove_entry(request):
    if request.method != 'DELETE':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    data = json.loads(request.body or '{}')
    entry_id = data.get('id')
    if not entry_id:
        return JsonResponse({'code': 400, 'message': 'id is required', 'data': {}}, status=400)

    entry = get_object_or_404(TimetableEntry, id=entry_id, user=u)
    entry.delete()
    return JsonResponse({'code': 200, 'message': 'Course removed successfully', 'data': {}})


def get_config(request):
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    config, _ = TimetableConfig.objects.get_or_create(user=u, defaults={'periods': DEFAULT_PERIODS})
    return JsonResponse({
        'code': 200,
        'message': 'Timetable config retrieved successfully',
        'data': {'periods': config.periods, 'total': len(config.periods)},
    })


def save_config(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Method Not Allowed', 'data': {}}, status=405)
    u = _require_user(request)
    if not isinstance(u, User):
        return u

    data = json.loads(request.body or '{}')
    raw_periods = data.get('periods')
    if not isinstance(raw_periods, list) or not raw_periods:
        return JsonResponse({'code': 400, 'message': 'periods 必须是非空列表', 'data': {}}, status=400)
    if len(raw_periods) > MAX_PERIODS:
        return JsonResponse({'code': 400, 'message': f'节次数不能超过 {MAX_PERIODS} 节', 'data': {}}, status=400)

    periods = []
    for item in raw_periods:
        start = str(item.get('start', '')).strip()
        end = str(item.get('end', '')).strip()
        if not TIME_RE.match(start) or not TIME_RE.match(end):
            return JsonResponse({'code': 400, 'message': '时间格式必须为 HH:MM', 'data': {}}, status=400)
        if end <= start:
            return JsonResponse({'code': 400, 'message': '每节的结束时间必须晚于开始时间', 'data': {}}, status=400)
        periods.append({'start': start, 'end': end})

    # 按顺序重新编号 1..N
    periods = [{'n': i + 1, **p} for i, p in enumerate(periods)]

    config, _ = TimetableConfig.objects.get_or_create(user=u, defaults={'periods': periods})
    config.periods = periods
    config.save(update_fields=['periods', 'updated_time'])
    return JsonResponse({
        'code': 200,
        'message': 'Timetable config saved successfully',
        'data': {'periods': config.periods, 'total': len(config.periods)},
    })
