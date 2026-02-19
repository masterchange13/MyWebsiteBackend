"""
ASGI config for MyWebsiteBackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyWebsiteBackend.settings')
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

django_asgi_app = get_asgi_application()

import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(chat.routing.websocket_urlpatterns),
})
