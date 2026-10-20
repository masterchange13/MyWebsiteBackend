from django.urls import path
from .consumers import TerminalConsumer

websocket_urlpatterns = [path('terminal/ws/', TerminalConsumer.as_asgi())]
