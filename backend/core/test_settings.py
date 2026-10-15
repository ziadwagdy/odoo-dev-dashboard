"""Settings for the automated tests: no Redis, no host paths, fast password hashing."""
import os
import tempfile

os.environ.setdefault('SECRET_KEY', 'test-only-not-a-secret')

from .settings import *  # noqa: E402,F401,F403

_TMP = tempfile.mkdtemp(prefix='dashboard-tests-')

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
DATA_DIR = os.path.join(_TMP, 'data')
ODOO_DEV_BASE = os.path.join(_TMP, 'odoo-dev')
REGISTRY_FILE = os.path.join(_TMP, 'odoo-dev', '.port-registry')
DB_USER = 'odoo_app'
DB_PASSWORD = 'shared-legacy-password'
ALLOWED_HOSTS = ['*']
