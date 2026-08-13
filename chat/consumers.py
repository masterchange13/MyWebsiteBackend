import json
import re
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage
from chat.services import presence_service

ONLINE_BROADCAST_GROUP = "chat_online_broadcast"


def _safe_group_name(name):
    """组名只允许 ASCII 字母数字、连字符、下划线、句点，长度 < 100"""
    cleaned = re.sub(r'[^a-zA-Z0-9\-_.]', '_', str(name))[:99]
    return cleaned or '_'


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope['query_string'].decode() if self.scope.get('query_string') else '')
        self.peer = (query.get('peer') or [''])[0]
        # 优先使用前端显式传递的 username 参数
        # 不要优先从 session 读取，因为同一浏览器的 session cookie 是共享的，
        # 多标签页登录不同账户时 session 会被最后一个登录的用户覆盖
        self.username = (query.get('username') or [''])[0]
        if not self.username:
            session = self.scope.get('session')
            self.username = session.get('user') if session else ''
        if not self.username:
            await self.close(code=4401)
            return
        self.connection_id = self.channel_name
        self.user_group = f'user_{_safe_group_name(self.username)}'

        # 加入个人组（用于定向消息路由）
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        # 加入在线广播组（用于接收在线状态变更通知）
        await self.channel_layer.group_add(ONLINE_BROADCAST_GROUP, self.channel_name)

        # 标记该连接在线，并刷新用户 presence TTL
        await sync_to_async(presence_service.mark_connection_online)(self.username, self.connection_id)

        await self.accept()

        # 连接建立后再广播，避免新旧客户端在握手阶段错过事件
        await self._broadcast_online_status(self.username, True)
        await self._broadcast_online_snapshot()

    async def disconnect(self, close_code):
        if self.username:
            # 从个人组移除
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            # 从广播组移除
            await self.channel_layer.group_discard(ONLINE_BROADCAST_GROUP, self.channel_name)

            # 标记当前连接下线；若用户仍有其他连接，则保持在线
            still_online = await sync_to_async(presence_service.mark_connection_offline)(
                self.username,
                getattr(self, 'connection_id', ''),
            )

            # 仅在最后一个连接断开时广播下线
            if not still_online:
                await self._broadcast_online_status(self.username, False)
                await self._broadcast_online_snapshot()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data or '{}')
        except Exception:
            data = {}
        if data.get('type') in {'heartbeat', 'ping'}:
            await sync_to_async(presence_service.refresh_connection)(
                self.username,
                getattr(self, 'connection_id', ''),
            )
            await self.send(text_data=json.dumps({
                'type': 'pong',
            }))
            return
        message = data.get('data') or data.get('message') or data.get('content') or ''
        to = data.get('receiveUsername') or data.get('to') or data.get('receiver') or self.peer or ''
        sender_name = self.username or ''

        # 保存消息
        sender = await sync_to_async(lambda: User.objects.filter(username=sender_name).first())() if sender_name else None
        receiver = await sync_to_async(lambda: User.objects.filter(username=to).first())() if to else None
        if to and receiver is None:
            await self.send(text_data=json.dumps({
                'sendUsername': 'system',
                'receiveUsername': sender_name,
                'data': f'用户不存在：{to}',
            }))
            return
        if message:
            msg_obj = await sync_to_async(ChatMessage.objects.create)(sender=sender, receiver=receiver, content=message)
            created_time = msg_obj.created_time.isoformat() if msg_obj else timezone.now().isoformat()
        else:
            created_time = timezone.now().isoformat()

        payload = {
            'type': 'chat.message',
            'sendUsername': sender_name,
            'receiveUsername': to or None,
            'data': message,
            'created_time': created_time,
        }
        # 路由消息：只发送给对话双方
        if to:
            await self.channel_layer.group_send(f'user_{_safe_group_name(to)}', payload)
        if sender_name:
            await self.channel_layer.group_send(f'user_{_safe_group_name(sender_name)}', payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'sendUsername': event.get('sendUsername'),
            'receiveUsername': event.get('receiveUsername'),
            'data': event.get('data'),
            'created_time': event.get('created_time'),
        }))

    async def online_status(self, event):
        """在线状态变更通知"""
        await self.send(text_data=json.dumps({
            'type': 'online_status',
            'username': event.get('username'),
            'online': event.get('online'),
        }))

    async def online_snapshot(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_snapshot',
            'users': event.get('users', []),
        }))

    async def _broadcast_online_status(self, username: str, online: bool):
        """向所有在线用户广播某用户的上线/下线状态"""
        await self.channel_layer.group_send(
            ONLINE_BROADCAST_GROUP,
            {
                'type': 'online.status',
                'username': username,
                'online': online,
            }
        )

    async def _broadcast_online_snapshot(self):
        users = await sync_to_async(presence_service.get_online_usernames)()
        await self.channel_layer.group_send(
            ONLINE_BROADCAST_GROUP,
            {
                'type': 'online.snapshot',
                'users': sorted(users),
            }
        )
