from django.conf import settings
from users.access import current_user, refresh_user


def allowed(user):
    return bool(user and settings.TERMINAL_ENABLED and user.is_advanced)
