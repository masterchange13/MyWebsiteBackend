from django.conf import settings
from importlib import import_module
from users.models.user_model import User


def current_user(session):
    username = session.get('user') if session else None
    return User.objects.filter(username=username).first() if username else None


def allowed(user):
    return bool(user and settings.TERMINAL_ENABLED and user.can_use_terminal)


def refresh_user(session):
    if not session or not session.session_key:
        return None
    store = import_module(settings.SESSION_ENGINE).SessionStore(session_key=session.session_key)
    return current_user(store)
