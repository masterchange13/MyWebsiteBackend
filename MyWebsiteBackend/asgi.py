"""
ASGI config for MyWebsiteBackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyWebsiteBackend.settings')

# 解决 Daphne (Twisted 异步事件循环) 与 Django @async_unsafe 的兼容性问题
# Django 的 ORM 操作被标记为 async_unsafe，Daphne 的 Twisted 事件循环可能不被
# asgiref 的 sync_to_async 正确识别，导致同步数据库操作被拒绝。
# 设置此环境变量允许在异步上下文中调用同步 ORM，因为本项目的视图全部是同步函数，
# 不存在并发数据库写入的风险。
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack

# 必须先初始化 Django ASGI 应用，再导入 Channels 路由
django_asgi_app = get_asgi_application()

import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": SessionMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns)),
})
