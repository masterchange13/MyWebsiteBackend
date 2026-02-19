import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from users.models.user_model import User
from chat.models.chat_message_model import ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope['query_string'].decode() if self.scope.get('query_string') else '')
        self.username = (query.get('username') or [''])[0]
        if self.username:
            await sync_to_async(User.objects.get_or_create)(
                username=self.username,
                defaults={'password': '', 'email': f'{self.username}@local'}
            )
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
        to = data.get('receiveUsername') or data.get('to') or data.get('receiver') or ''
        sender_name = self.username
        # 保存消息
        sender = await sync_to_async(lambda: User.objects.filter(username=sender_name).first())() if sender_name else None
        # 如果对方用户不存在，自动创建占位账号，保证持久化与历史查询一致
        receiver = None
        if to:
            receiver = await sync_to_async(lambda: User.objects.filter(username=to).first())()
            if receiver is None:
                receiver = await sync_to_async(lambda: User.objects.create(username=to, password='', email=f'{to}@local'))()
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
