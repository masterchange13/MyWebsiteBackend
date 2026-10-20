import asyncio
import contextlib
import json
import logging
import threading
import time
import uuid
from urllib.parse import parse_qs, urlsplit

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core import signing
from django.core.cache import cache

from terminal.access import current_user, allowed, refresh_user
from terminal.console import Console

logger = logging.getLogger(__name__)
LEASE_TIMEOUT = 45


def origin_allowed(scope):
    headers = dict(scope.get('headers', []))
    origin = headers.get(b'origin', b'').decode('utf-8', errors='replace')
    parsed = urlsplit(origin)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path:
        return False
    host = headers.get(b'host', b'').decode('utf-8', errors='replace')
    return parsed.netloc == host or origin in settings.CSRF_TRUSTED_ORIGINS


class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.console = None
        self.pump = None
        self.reader = None
        self.stop_reader = threading.Event()
        self.lease = None
        self.lease_id = uuid.uuid4().hex
        if not origin_allowed(self.scope):
            await self.close(code=4403)
            return
        try:
            if len(self.scope.get('query_string', b'')) > 4096:
                raise ValueError()
            query = parse_qs(self.scope.get('query_string', b'').decode())
            token = (query.get('token') or [''])[0]
            payload = signing.loads(token, salt='website-terminal', max_age=60)
            if not isinstance(payload, dict) or not isinstance(payload.get('nonce'), str) or len(payload['nonce']) != 32:
                raise ValueError()
        except (signing.BadSignature, ValueError, UnicodeError):
            await self.close(code=4403)
            return
        user = await database_sync_to_async(current_user)(self.scope.get('session'))
        if not allowed(user) or payload.get('uid') != getattr(user, 'pk', None):
            await self.close(code=4403)
            return
        if payload.get('sid') != self.scope['session'].session_key or not payload.get('nonce'):
            await self.close(code=4403)
            return
        token_key = f"terminal-token-used:{payload['nonce']}"
        if not await asyncio.to_thread(cache.add, token_key, True, 65):
            await self.close(code=4403)
            return
        lease = f'terminal-session:{user.pk}'
        if not await asyncio.to_thread(cache.add, lease, self.lease_id, LEASE_TIMEOUT):
            await self.accept()
            await self.send(text_data=json.dumps({'type': 'error', 'reason': 'connection_exists', 'message': '此账号已有终端连接，请点击“关闭已有连接”后重试。'}))
            await self.close(code=4429)
            return
        self.lease = lease
        await self.accept()
        try:
            self.console = await asyncio.to_thread(Console)
        except Exception:
            logger.exception('Unable to start terminal')
            await self.send(text_data=json.dumps({'type': 'error', 'message': '终端启动失败，请检查服务器 Shell 和终端依赖。'}))
            await self.release_lease()
            await self.close(code=4500)
            return
        self.last_input = time.monotonic()
        self.last_lease_refresh = self.last_input
        self.last_auth_check = self.last_input
        self.queue = asyncio.Queue(maxsize=64)
        self.loop = asyncio.get_running_loop()
        self.reader = threading.Thread(target=self.read_output, daemon=True, name='web-terminal-output')
        self.reader.start()
        self.pump = asyncio.create_task(self.send_output())
        await self.send(text_data=json.dumps({'type': 'ready'}))

    def read_output(self):
        try:
            while not self.stop_reader.is_set():
                chunk = self.console.read()
                if chunk:
                    future = asyncio.run_coroutine_threadsafe(self.queue.put(chunk), self.loop)
                    try:
                        future.result(timeout=2)
                    except Exception:
                        future.cancel()
                        break
        except (EOFError, OSError):
            pass
        finally:
            if not self.stop_reader.is_set():
                future = asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
                try:
                    future.result(timeout=2)
                except Exception:
                    future.cancel()

    async def send_output(self):
        try:
            while True:
                if time.monotonic() - self.last_auth_check >= 5:
                    user = await database_sync_to_async(refresh_user)(self.scope.get('session'))
                    if not allowed(user):
                        await self.send(text_data=json.dumps({'type': 'error', 'message': '终端权限已撤销或登录已失效，连接已关闭。'}))
                        break
                    self.last_auth_check = time.monotonic()
                if not await self.owns_connection():
                    await self.send(text_data=json.dumps({'type': 'error', 'message': '此终端连接已关闭，可以重新连接。'}))
                    break
                if time.monotonic() - self.last_lease_refresh >= 10:
                    await asyncio.to_thread(cache.touch, self.lease, LEASE_TIMEOUT)
                    self.last_lease_refresh = time.monotonic()
                if time.monotonic() - self.last_input > settings.TERMINAL_IDLE_TIMEOUT:
                    await self.send(text_data=json.dumps({'type': 'error', 'message': '终端长时间未操作，连接已关闭。'}))
                    break
                try:
                    chunk = await asyncio.wait_for(self.queue.get(), timeout=1)
                except asyncio.TimeoutError:
                    continue
                if chunk is None:
                    break
                await self.send(text_data=json.dumps({'type': 'output', 'data': chunk}))
        finally:
            self.stop_reader.set()
            if self.console:
                await asyncio.to_thread(self.console.close)
            await self.release_lease()
            await self.close()

    async def release_lease(self):
        if self.lease:
            if await asyncio.to_thread(cache.get, self.lease) == self.lease_id:
                await asyncio.to_thread(cache.delete, self.lease)
            self.lease = None
        await asyncio.to_thread(cache.delete, f'terminal-stop:{self.lease_id}')

    async def owns_connection(self):
        if not self.lease or await asyncio.to_thread(cache.get, f'terminal-stop:{self.lease_id}'):
            return False
        return await asyncio.to_thread(cache.get, self.lease) == self.lease_id

    async def receive(self, text_data=None, bytes_data=None):
        if not self.console or not text_data or len(text_data) > 32768:
            return
        if not await self.owns_connection():
            await self.close(code=4400)
            return
        try:
            data = json.loads(text_data)
            if not isinstance(data, dict):
                return
            if data.get('type') == 'input' and isinstance(data.get('data'), str):
                self.last_input = time.monotonic()
                await asyncio.to_thread(self.console.write, data['data'])
            elif data.get('type') == 'resize':
                rows = max(5, min(120, int(data.get('rows', 24))))
                cols = max(20, min(400, int(data.get('cols', 80))))
                await asyncio.to_thread(self.console.resize, rows, cols)
            elif data.get('type') == 'ping':
                user = await database_sync_to_async(refresh_user)(self.scope.get('session'))
                if not allowed(user):
                    await self.close(code=4403)
                    return
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except (ValueError, TypeError, EOFError, OSError):
            return

    async def disconnect(self, close_code):
        self.stop_reader.set()
        if self.pump:
            self.pump.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.pump
        elif self.console:
            await asyncio.to_thread(self.console.close)
        await self.release_lease()
        if self.reader:
            await asyncio.to_thread(self.reader.join, 1)
