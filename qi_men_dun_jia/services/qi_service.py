import json
import threading
from datetime import datetime
from django.http import JsonResponse
from django.db import close_old_connections
from users.models.user_model import User
from qi_men_dun_jia.models import QimenCalculation, QimenPalace
from qi_men_dun_jia.services.deepseek_client import call_deepseek
import os
from django.utils import timezone

def _safe_parse_datetime(dt_str: str):
    fmts = ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"]
    for f in fmts:
        try:
            return datetime.strptime(dt_str, f)
        except Exception:
            continue
    return None

def _seed_from(dt: datetime, location: str, topic: str, solar: bool) -> int:
    base = int(dt.timestamp()) if dt else 0
    return (base ^ hash(location or '') ^ hash(topic or '') ^ (1 if solar else 0)) & 0xffffffff

def _gen_simple_chart(seed: int, topic: str):
    gates = ['休','生','伤','杜','景','死','惊','开']
    stars = ['天蓬','天任','天冲','天辅','天英','天芮','天柱','天心','天禽']
    gods  = ['值符','值使','螣蛇','朱雀','六合','白虎','玄武','九地','九天']
    palaces = []
    for i in range(9):
        g = gates[(seed + i) % len(gates)]
        s = stars[(seed // 3 + i) % len(stars)]
        d = gods[(seed // 7 + i) % len(gods)]
        tip = (topic + '：' if topic else '') + f'{g}、{s}、{d}'
        palaces.append({
            'index': i + 1,
            'gate': g,
            'star': s,
            'god' : d,
            'tip' : tip,
        })
    return palaces

def _build_analysis_prompt(calc: QimenCalculation, palaces):
    return f"时间：{calc.datetime_str}\n地点：{calc.location}\n主题：{calc.topic}\n阳历：{calc.solar}\n\n九宫：\n" + "\n".join(
        [f"{p['index']}宫 门:{p['gate']} 星:{p['star']} 神:{p['god']} 提示:{p['tip']}" for p in palaces]
    ) + "\n\n请结合主题给出分析与建议。"

def _serialize_calc(calc: QimenCalculation):
    palaces = list(calc.palaces.order_by('index').values('index', 'gate', 'star', 'god', 'tip'))
    return {
        'input': {
            'datetime': calc.datetime_str,
            'location': calc.location,
            'topic': calc.topic,
            'solar': calc.solar,
        },
        'meta': {
            'parsed_datetime': calc.parsed_datetime.isoformat() if calc.parsed_datetime else None,
            'seed': calc.seed,
        },
        'chart': palaces,
        'id': calc.id,
        'analysis_status': calc.analysis_status,
        'analysis_error': calc.analysis_error,
        'analysis': {
            'text': calc.analysis_text,
            'provider': calc.analysis_provider,
            'model': calc.analysis_model,
        } if calc.analysis_text else None,
    }

def _run_analysis(calc_id: int, api_key: str = ''):
    close_old_connections()
    try:
        calc = QimenCalculation.objects.filter(id=calc_id).first()
        if not calc:
            return
        calc.analysis_status = 'running'
        calc.analysis_error = ''
        calc.save(update_fields=['analysis_status', 'analysis_error'])

        palaces = list(calc.palaces.order_by('index').values('index', 'gate', 'star', 'god', 'tip'))
        prompt = _build_analysis_prompt(calc, palaces)
        text, err = call_deepseek(api_key, prompt)

        calc = QimenCalculation.objects.filter(id=calc_id).first()
        if not calc:
            return
        if text:
            calc.analysis_text = text
            calc.analysis_provider = 'deepseek'
            calc.analysis_model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')
            calc.analysis_time = timezone.now()
            calc.analysis_status = 'success'
            calc.analysis_error = ''
            calc.save(update_fields=[
                'analysis_text',
                'analysis_provider',
                'analysis_model',
                'analysis_time',
                'analysis_status',
                'analysis_error',
            ])
        else:
            calc.analysis_status = 'failed'
            calc.analysis_error = err or '分析失败'
            calc.save(update_fields=['analysis_status', 'analysis_error'])
    finally:
        close_old_connections()

def _start_analysis_task(calc_id: int, api_key: str = ''):
    thread = threading.Thread(target=_run_analysis, args=(calc_id, api_key), daemon=True)
    thread.start()

def calc(request):
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}
    dt_str = data.get('datetime')
    location = data.get('location') or ''
    topic = data.get('topic') or ''
    solar = bool(data.get('solar', True))

    dt = _safe_parse_datetime(dt_str) if dt_str else None
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    seed = _seed_from(dt, location, topic, solar)
    chart = _gen_simple_chart(seed, topic)

    session_user = request.session.get('user')
    user = None
    if session_user:
        user = User.objects.filter(username=session_user).first()
    calc = QimenCalculation.objects.create(
        user=user,
        datetime_str=dt_str or '',
        location=location,
        topic=topic,
        solar=solar,
        parsed_datetime=dt,
        seed=seed,
        analysis_status='pending' if bool(data.get('analyze', False)) else 'none',
    )
    for i, p in enumerate(chart):
        QimenPalace.objects.create(
            calc=calc,
            index=p.get('index') or (i + 1),
            gate=p.get('gate') or '',
            star=p.get('star') or '',
            god=p.get('god') or '',
            tip=p.get('tip') or '',
        )

    if bool(data.get('analyze', False)):
        api_key = data.get('api_key') or os.environ.get('DEEPSEEK_API_KEY', '')
        _start_analysis_task(calc.id, api_key)

    resp = _serialize_calc(calc)
    return JsonResponse({'code': 200, 'message': 'success', 'data': resp})

def result(request, calc_id):
    calc = QimenCalculation.objects.filter(id=calc_id).first()
    if not calc:
        return JsonResponse({'code': 404, 'message': '记录不存在', 'data': {}}, status=404)
    return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_calc(calc)})

def history(request):
    session_user = request.session.get('user')
    qs = QimenCalculation.objects.all()
    if session_user:
        user = User.objects.filter(username=session_user).first()
        qs = qs.filter(user=user) if user else qs.none()
    else:
        qs = qs.filter(user__isnull=True)

    records = []
    for calc in qs.order_by('-created_time')[:30]:
        records.append({
            'id': calc.id,
            'datetime': calc.datetime_str,
            'location': calc.location,
            'topic': calc.topic,
            'solar': calc.solar,
            'analysis_status': calc.analysis_status,
            'created_time': calc.created_time.isoformat() if calc.created_time else None,
        })
    return JsonResponse({'code': 200, 'message': 'success', 'data': {'records': records}})

def analyze(request):
    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}
    calc_id = data.get('id')
    api_key = data.get('api_key') or os.environ.get('DEEPSEEK_API_KEY', '')
    if calc_id:
        calc = QimenCalculation.objects.filter(id=calc_id).first()
        if not calc:
            return JsonResponse({'code': 404, 'message': '记录不存在', 'data': {}}, status=404)
        if calc.analysis_status in ('pending', 'running'):
            return JsonResponse({'code': 202, 'message': '分析进行中', 'data': _serialize_calc(calc)})
        if calc.analysis_text and calc.analysis_status == 'success':
            return JsonResponse({'code': 200, 'message': 'success', 'data': _serialize_calc(calc)})
        calc.analysis_status = 'pending'
        calc.analysis_error = ''
        calc.save(update_fields=['analysis_status', 'analysis_error'])
        _start_analysis_task(calc.id, api_key)
        return JsonResponse({'code': 202, 'message': '分析已开始', 'data': _serialize_calc(calc)})
    else:
        # 无 id，则以入参生成一次并分析
        # 复用 calc 逻辑，带 analyze=true
        data['analyze'] = True
        request._body = json.dumps(data).encode('utf-8')
        return calc(request)
