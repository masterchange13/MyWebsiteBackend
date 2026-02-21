import json
from datetime import datetime
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from users.models.user_model import User
from qi_men_dun_jia.models import QimenCalculation, QimenPalace
from qi_men_dun_jia.services.deepseek_client import call_deepseek
import os
from datetime import datetime as dtmod

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
        prompt = f"时间：{dt_str}\n地点：{location}\n主题：{topic}\n阳历：{solar}\n\n九宫：\n" + "\n".join(
            [f"{p['index']}宫 门:{p['gate']} 星:{p['star']} 神:{p['god']} 提示:{p['tip']}" for p in chart]
        ) + "\n\n请结合主题给出分析与建议。"
        text, err = call_deepseek(api_key, prompt)
        if text:
            calc.analysis_text = text
            calc.analysis_provider = 'deepseek'
            calc.analysis_model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')
            calc.analysis_time = dtmod.utcnow()
            calc.save()
        else:
            return JsonResponse({'code': 502, 'message': f'分析失败: {err}', 'data': {'id': calc.id}})

    resp = {
        'input': {
            'datetime': dt_str,
            'location': location,
            'topic': topic,
            'solar': solar,
        },
        'meta': {
            'parsed_datetime': dt.isoformat() if dt else None,
            'seed': seed,
        },
        'chart': chart,
        'id': calc.id,
        'analysis': {'text': calc.analysis_text, 'provider': calc.analysis_provider, 'model': calc.analysis_model} if calc.analysis_text else None,
    }
    print("anslaysis", calc.analysis_text)
    return JsonResponse({'code': 200, 'message': 'success', 'data': resp})

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
        palaces = list(calc.palaces.order_by('index').values('index','gate','star','god','tip'))
        prompt = f"时间：{calc.datetime_str}\n地点：{calc.location}\n主题：{calc.topic}\n阳历：{calc.solar}\n\n九宫：\n" + "\n".join(
            [f"{p['index']}宫 门:{p['gate']} 星:{p['star']} 神:{p['god']} 提示:{p['tip']}" for p in palaces]
        ) + "\n\n请结合主题给出分析与建议。"
        text, err = call_deepseek(api_key, prompt)
        if not text:
            return JsonResponse({'code': 502, 'message': f'分析失败: {err}', 'data': {'id': calc.id}})
        calc.analysis_text = text
        calc.analysis_provider = 'deepseek'
        calc.analysis_model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')
        calc.analysis_time = dtmod.utcnow()
        calc.save()
        return JsonResponse({'code': 200, 'message': 'success', 'data': {'id': calc.id, 'analysis': {'text': text, 'provider': calc.analysis_provider, 'model': calc.analysis_model}}})
    else:
        # 无 id，则以入参生成一次并分析
        # 复用 calc 逻辑，带 analyze=true
        data['analyze'] = True
        request._body = json.dumps(data).encode('utf-8')
        return calc(request)
