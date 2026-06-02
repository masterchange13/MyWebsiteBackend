import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        session = self.scope.get('session')
        self.username = session.get('user') if session else ''
        query = parse_qs(self.scope['query_string'].decode() if self.scope.get('query_string') else '')
        self.peer = (query.get('peer') or [''])[0]
        if not self.username:
            await self.close(code=4401)
            return
        # 加入全局群组
        self.room_group_name = 'chat'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # 加入个人组
        if self.username:
            await self.channel_layer.group_add(f'user_{self.username}', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if self.username:
            await self.channel_layer.group_discard(f'user_{self.username}', self.channel_name)

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
            await sync_to_async(ChatMessage.objects.create)(sender=sender, receiver=receiver, content=message)
        payload = {
            'type': 'chat.message',
            'sendUsername': sender_name,
            'receiveUsername': to or None,
            'data': message,
        }
        # 路由消息
        if to:
            await self.channel_layer.group_send(f'user_{to}', payload)
            if sender_name:
                await self.channel_layer.group_send(f'user_{sender_name}', payload)
        else:
            await self.channel_layer.group_send(self.room_group_name, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'sendUsername': event.get('sendUsername'),
            'receiveUsername': event.get('receiveUsername'),
            'data': event.get('data'),
        }))
