"""Self-contained test database and channels; never uses deployment services."""
from .settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
