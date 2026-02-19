from django.urls import path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    path('chat/ws', ChatConsumer.as_asgi()),
]
