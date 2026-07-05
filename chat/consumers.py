import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage

ONLINE_USERS_KEY = "chat:online_users"  # Redis Set
ONLINE_BROADCAST_GROUP = "chat:online_broadcast"


def _get_redis():
    """获取原始 Redis 客户端，用于 Set 操作"""
    return cache.client.get_client()


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

        # 加入个人组（用于定向消息路由）
        await self.channel_layer.group_add(f'user_{self.username}', self.channel_name)
        # 加入在线广播组（用于接收在线状态变更通知）
        await self.channel_layer.group_add(ONLINE_BROADCAST_GROUP, self.channel_name)

        # Redis SADD: 标记用户上线
        await sync_to_async(_get_redis().sadd)(ONLINE_USERS_KEY, self.username)

        # 广播上线通知给所有在线用户
        await self._broadcast_online_status(self.username, True)

        await self.accept()

    async def disconnect(self, close_code):
        if self.username:
            # 从个人组移除
            await self.channel_layer.group_discard(f'user_{self.username}', self.channel_name)
            # 从广播组移除
            await self.channel_layer.group_discard(ONLINE_BROADCAST_GROUP, self.channel_name)

            # Redis SREM: 标记用户下线
            await sync_to_async(_get_redis().srem)(ONLINE_USERS_KEY, self.username)

            # 广播下线通知
            await self._broadcast_online_status(self.username, False)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data or '{}')
        except Exception:
            data = {}
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
            await self.channel_layer.group_send(f'user_{to}', payload)
        if sender_name:
            await self.channel_layer.group_send(f'user_{sender_name}', payload)

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
