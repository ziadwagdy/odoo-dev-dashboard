import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY environment variable must be set')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'corsheaders',
    'channels',
    'apps.projects',
    'apps.streams',
    'apps.database',
    'apps.git_ops',
    'apps.settings_app',
    'apps.notebooks',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    _cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(os.environ.get('DATA_DIR', '/app/data')) / 'dashboard.db',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.environ.get('REDIS_HOST', 'redis'), 6379)],
        },
    },
}

# App config
REGISTRY_FILE = os.environ.get('REGISTRY_FILE', '/srv/odoo-dev/projects/.port-registry')
BASE_DOMAIN = os.environ.get('BASE_DOMAIN', 'example.com')
_base = BASE_DOMAIN
LOGS_URL = os.environ.get('LOGS_URL', f'https://logs.{_base}')
FILES_URL = os.environ.get('FILES_URL', f'https://files.{_base}')
TERMINAL_URL = os.environ.get('TERMINAL_URL', f'https://terminal.{_base}')
DASHBOARD_TITLE = os.environ.get('DASHBOARD_TITLE', 'Odoo Dev Dashboard')
ODOO_DEV_BASE = os.environ.get('ODOO_DEV_BASE', '/srv/odoo-dev')
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
DB_USER = os.environ.get('DB_USER', 'odoo')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'odoo')
DB_HOST = os.environ.get('DB_HOST', 'host.docker.internal')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
