import pytest
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.projects.models import UserProjectAssignment
from core.authentication import mark_active

ROLES = ('admin', 'manager', 'developer')

CONF = """[options]
admin_passwd = {master}
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/enterprise-addons
data_dir = /var/lib/odoo
db_host = db-alpha
db_port = 5432
db_user = odoo_app
db_password = SUPERSECRET-DB-PASSWORD
list_db = False
workers = 2
max_cron_threads = 1
limit_memory_soft = 2147483648
limit_memory_hard = 2684354560
limit_time_cpu = 60
limit_time_real = 120
log_level = info
"""

MASTER = 'm' * 40


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def groups(db):
    return {name: Group.objects.get_or_create(name=name)[0] for name in ROLES}


@pytest.fixture
def make_user(db, groups):
    def _make(username, role='developer', projects=(), password='correct-horse-battery-staple'):
        user = User.objects.create_user(username=username, password=password)
        if role in groups:
            user.groups.add(groups[role])
        for project in projects:
            UserProjectAssignment.objects.create(user=user, project_name=project)
        return user
    return _make


@pytest.fixture
def client_for(db):
    def _client(user):
        token = Token.objects.create(user=user)
        mark_active(token.key)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        client.token_key = token.key
        return client
    return _client


@pytest.fixture
def anon(db):
    return APIClient()


@pytest.fixture
def odoo_base(tmp_path, settings, monkeypatch):
    """A fake ~/odoo-dev: registry with projects alpha and beta, alpha's odoo.conf, and
    an isolated secrets dir. Nothing outside tmp_path is touched."""
    base = tmp_path / 'odoo-dev'
    (base / 'alpha' / 'config').mkdir(parents=True)
    (base / 'beta' / 'config').mkdir(parents=True)
    (base / 'alpha' / 'config' / 'odoo.conf').write_text(CONF.format(master=MASTER))
    (base / 'beta' / 'config' / 'odoo.conf').write_text(CONF.format(master='b' * 40))
    (base / '.port-registry').write_text(
        'alpha|18|8069|15432|alpha.example.org|alpha/repo|alpha/config/odoo.conf\n'
        'beta|19|8070|15433|beta.example.org|beta/repo|beta/config/odoo.conf\n')
    settings.ODOO_DEV_BASE = str(base)
    settings.REGISTRY_FILE = str(base / '.port-registry')
    settings.DATA_DIR = str(tmp_path / 'data')
    from services import db_service
    monkeypatch.setattr(db_service, 'SECRETS_DIR', str(base / 'secrets'))
    return base
