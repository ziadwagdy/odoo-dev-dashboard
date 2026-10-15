import json

import pytest

from apps.projects.models import AuditLog


@pytest.fixture
def fakes(monkeypatch):
    calls = {}
    monkeypatch.setattr('apps.projects.views.create_odoo_database',
                        lambda proj, port, name, demo=False: calls.setdefault('create', (proj, name, demo)) and ('admin', 'pw-1'))
    monkeypatch.setattr('apps.projects.views.set_odoo_user_password',
                        lambda proj, port, db, login='admin': calls.setdefault('pw', (proj, db, login)) and 'pw-2')
    monkeypatch.setattr('apps.projects.views.sso_service.list_login_candidates',
                        lambda port, db: [{'login': 'admin', 'name': 'Admin', 'admin': True}, {'login': 'sara', 'name': 'Sara', 'admin': False}])
    monkeypatch.setattr('apps.projects.views.sso_service.database_state', lambda port, db: {'neutralized': True})
    monkeypatch.setattr('apps.projects.views.sso_service.build_login_url',
                        lambda p, port, db, login, **kw: calls.setdefault('url', (p['name'], db, login)) and 'https://x/dashboard/login?t=1')
    return calls


@pytest.fixture
def actors(odoo_base, make_user, client_for):
    return {
        'admin': client_for(make_user('root', role='admin')),
        'manager': client_for(make_user('mgr', role='manager', projects=['alpha'])),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
        'stranger': client_for(make_user('str', role='developer', projects=['beta'])),
    }


def _post(c, path, body=None):
    return c.post(path, json.dumps(body or {}), content_type='application/json')


def test_create_database_returns_credentials_once_without_caching(actors, fakes):
    r = _post(actors['dev'], '/api/db/alpha/create', {'name': 'scratch'})
    assert r.status_code == 200 and r.json() == {'ok': True, 'name': 'scratch', 'login': 'admin', 'password': 'pw-1'}
    assert r['Cache-Control'] == 'no-store'
    assert AuditLog.objects.filter(action='db_create', user='dev', project='alpha').exists()
    assert 'pw-1' not in ' '.join(AuditLog.objects.values_list('detail', flat=True))   # never audited


def test_create_database_respects_project_acl(actors, fakes):
    assert _post(actors['stranger'], '/api/db/alpha/create', {'name': 'x'}).status_code == 403
    assert 'create' not in fakes


def test_admin_password_is_manager_or_admin_only(actors, fakes):
    assert _post(actors['dev'], '/api/db/alpha/admin-password/db1').status_code == 403
    assert _post(actors['stranger'], '/api/db/alpha/admin-password/db1').status_code == 403
    r = _post(actors['manager'], '/api/db/alpha/admin-password/db1')
    assert r.status_code == 200 and r.json()['password'] == 'pw-2'
    assert AuditLog.objects.filter(action='db_admin_password', user='mgr').exists()


def test_login_link_is_audited_and_acl_checked(actors, fakes):
    assert _post(actors['stranger'], '/api/db/alpha/login-link/db1', {'login': 'sara'}).status_code == 403
    r = _post(actors['dev'], '/api/db/alpha/login-link/db1', {'login': 'sara'})
    assert r.status_code == 200 and r.json()['ok'] and r['Cache-Control'] == 'no-store'
    assert fakes['url'] == ('alpha', 'db1', 'sara')
    entry = AuditLog.objects.get(action='db_login_link')
    assert entry.user == 'dev' and 'db1 as sara' in entry.detail


def test_login_users_requires_project_access(actors, fakes):
    assert actors['stranger'].get('/api/db/alpha/login-users/db1').status_code == 403
    assert actors['dev'].get('/api/db/alpha/login-users/db1').json()['users'][0]['login'] == 'admin'


def test_deploy_and_delete_are_admin_only(actors):
    for role in ('manager', 'dev'):
        assert _post(actors[role], '/api/project/alpha/deploy').status_code == 403
        assert actors[role].delete('/api/project/alpha/delete').status_code == 403
