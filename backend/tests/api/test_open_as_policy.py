"""'Open as' is role-gated and audited with who/what/why (Phase 1, written first)."""
import json

import pytest

from apps.projects.models import AuditLog

USERS = [
    {'login': 'admin', 'name': 'Administrator', 'admin': True},
    {'login': 'sara', 'name': 'Sara', 'admin': False},
]


@pytest.fixture
def state(monkeypatch):
    s = {'neutralized': True, 'url_calls': []}
    monkeypatch.setattr('apps.projects.views.sso_service.list_login_candidates', lambda port, db: USERS)
    monkeypatch.setattr('apps.projects.views.sso_service.database_state', lambda port, db: {'neutralized': s['neutralized']})

    def build(project, port, db, login, **kw):
        s['url_calls'].append((db, login))
        return 'https://alpha.example.org/dashboard/login?t=x'
    monkeypatch.setattr('apps.projects.views.sso_service.build_login_url', build)
    return s


@pytest.fixture
def people(odoo_base, make_user, client_for):
    return {
        'admin': client_for(make_user('root', role='admin')),
        'manager': client_for(make_user('mgr', role='manager', projects=['alpha'])),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
        'viewer': client_for(make_user('view', role='viewer', projects=['alpha'])),
    }


def _open(client, login, reason=None, **extra):
    body = {'login': login}
    if reason is not None:
        body['reason'] = reason
    return client.post('/api/db/alpha/login-link/db1', json.dumps(body), content_type='application/json', **extra)


def test_developer_can_open_an_ordinary_user_of_a_neutralized_db(people, state):
    r = _open(people['dev'], 'sara')
    assert r.status_code == 200 and state['url_calls'] == [('db1', 'sara')]


def test_developer_cannot_open_the_administrator(people, state):
    r = _open(people['dev'], 'admin', reason='I really need to')
    assert r.status_code == 403 and state['url_calls'] == []


def test_developer_cannot_open_a_database_that_is_not_neutralized(people, state):
    state['neutralized'] = False
    assert _open(people['dev'], 'sara', reason='quick look').status_code == 403
    assert state['url_calls'] == []


def test_viewer_role_cannot_open_anything(people, state):
    assert _open(people['viewer'], 'sara').status_code == 403


def test_manager_needs_a_reason_for_the_administrator(people, state):
    r = _open(people['manager'], 'admin')
    assert r.status_code == 400 and r.json()['reason_required'] is True
    assert state['url_calls'] == []
    assert _open(people['manager'], 'admin', reason='verify ACL for ticket 4521').status_code == 200


def test_manager_cannot_open_the_administrator_of_a_non_neutralized_db(people, state):
    state['neutralized'] = False
    assert _open(people['manager'], 'admin', reason='verify something important').status_code == 403


def test_admin_on_non_neutralized_db_needs_a_reason(people, state):
    state['neutralized'] = False
    assert _open(people['admin'], 'sara').status_code == 400
    assert _open(people['admin'], 'sara', reason='customer data repair 4521').status_code == 200


def test_unknown_login_is_a_400(people, state):
    assert _open(people['admin'], 'nobody').status_code == 400


def test_login_users_lists_what_the_caller_may_do(people, state):
    users = people['dev'].get('/api/db/alpha/login-users/db1').json()
    by_login = {u['login']: u for u in users['users']}
    assert by_login['sara']['allowed'] is True and by_login['admin']['allowed'] is False
    assert by_login['admin']['why'] and users['neutralized'] is True


def test_login_users_marks_where_a_reason_is_needed(people, state):
    state['neutralized'] = False
    users = people['admin'].get('/api/db/alpha/login-users/db1').json()
    assert all(u['reason_required'] for u in users['users'])
    assert users['neutralized'] is False


def test_successful_open_is_audited_with_who_whom_why_and_where_from(people, state):
    _open(people['manager'], 'admin', reason='verify ACL for ticket 4521', HTTP_CF_CONNECTING_IP='203.0.113.5')
    entry = AuditLog.objects.get(action='db_login_link', outcome='success')
    assert entry.user == 'mgr' and entry.project == 'alpha'
    assert entry.ip == '203.0.113.5'
    assert entry.meta == {'db': 'db1', 'target': 'admin', 'target_is_admin': True, 'neutralized': True,
                          'reason': 'verify ACL for ticket 4521', 'expires_in': 60}


def test_denied_attempts_are_audited_too(people, state):
    _open(people['dev'], 'admin', reason='please')
    entry = AuditLog.objects.get(action='db_login_link')
    assert entry.outcome == 'denied' and entry.user == 'dev' and entry.meta['target'] == 'admin'
