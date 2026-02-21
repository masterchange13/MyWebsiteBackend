import os
import json
import urllib.request

DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')

try:
    from qi_men_dun_jia.local_secret import DEEPSEEK_API_KEY as LOCAL_DEEPSEEK_API_KEY
except Exception:
    LOCAL_DEEPSEEK_API_KEY = ""

def _resolve_api_key(explicit: str = "") -> str:
    if explicit:
        return explicit
    if LOCAL_DEEPSEEK_API_KEY:
        return LOCAL_DEEPSEEK_API_KEY
    return os.environ.get('DEEPSEEK_API_KEY', '')

def call_deepseek(api_key: str, prompt: str):
    key = _resolve_api_key(api_key)
    if not key:
        return None, 'DeepSeek API key not configured'
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是精通奇门遁甲的分析专家，请依据输入的盘面给出清晰、可执行的分析建议。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_API_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {key}')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            parsed = json.loads(body)
            text = parsed.get('choices', [{}])[0].get('message', {}).get('content')
            return text, None
    except Exception as e:
        return None, str(e)
