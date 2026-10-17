"""The Modules tab: list, update selected, update all. Written first."""
import json

import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient

from apps.projects.models import AuditLog


@pytest.fixture
def actors(odoo_base, make_user, client_for):
    return {
        'admin': client_for(make_user('root', role='admin')),
        'manager': client_for(make_user('mgr', role='manager', projects=['alpha'])),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
        'stranger': client_for(make_user('str', role='manager', projects=['beta'])),
    }


def _post(c, path):
    return c.post(path, json.dumps({}), content_type='application/json')


# ── module list ────────────────────────────────────────────────────────────
def test_module_list_requires_project_access(actors, monkeypatch):
    monkeypatch.setattr('apps.projects.views.list_modules_grouped', lambda *a, **k: {'custom': [], 'standard': []})
    assert actors['stranger'].get('/api/modules/alpha/db1').status_code == 403
    assert actors['dev'].get('/api/modules/alpha/db1').status_code == 200


def test_module_list_rejects_unsafe_database_names(actors, monkeypatch):
    monkeypatch.setattr('apps.projects.views.list_modules_grouped', lambda *a, **k: {})
    assert actors['dev'].get('/api/modules/alpha/db%3Bdrop').status_code in (400, 404)


# ── starting an update ─────────────────────────────────────────────────────
def test_update_hands_out_a_stream_url_for_managers_and_admins(actors):
    r = _post(actors['manager'], '/api/modules/alpha/db1/update/sale')
    assert r.status_code == 200 and r.json() == {'ok': True, 'stream_url': '/stream/module-update/alpha/db1/sale'}
    assert _post(actors['admin'], '/api/modules/alpha/db1/update/all').json()['stream_url'].endswith('/db1/all')


def test_update_accepts_comma_joined_selections(actors):
    r = _post(actors['manager'], '/api/modules/alpha/db1/update/sale,purchase,stock')
    assert r.status_code == 200 and r.json()['stream_url'].endswith('/db1/sale,purchase,stock')


def test_developers_are_refused_upfront_not_after_the_stream_opens(actors):
    r = _post(actors['dev'], '/api/modules/alpha/db1/update/sale')
    assert r.status_code == 403 and r.json().get('ok') is False


def test_other_projects_members_are_refused(actors):
    assert _post(actors['stranger'], '/api/modules/alpha/db1/update/sale').status_code == 403


@pytest.mark.parametrize('module', ['sale;rm', 'a%20b', '..%2Fx', '%24%28id%29'])
def test_unsafe_module_names_are_rejected_before_any_stream(actors, module):
    r = _post(actors['manager'], f'/api/modules/alpha/db1/update/{module}')
    assert r.status_code in (400, 404)
    if r.status_code == 400:
        assert r.json()['ok'] is False


def test_starting_an_update_is_audited(actors):
    _post(actors['manager'], '/api/modules/alpha/db1/update/sale')
    entry = AuditLog.objects.get(action='module_update')
    assert entry.user == 'mgr' and entry.project == 'alpha' and 'db1' in entry.detail and 'sale' in entry.detail


# ── the stream: all / many / failure ───────────────────────────────────────
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('module', ['all', 'sale,purchase'])
def test_stream_runs_the_update_for_all_and_for_lists(actors, monkeypatch, module):
    seen = {}

    def fake(project, port, db, mod, emit, backup_dir, **kw):
        seen['args'] = (project, db, mod)
        emit('Taking a safety snapshot before updating…')
        emit('odoo: modules loaded')
        return 0
    monkeypatch.setattr('apps.streams.views.lifecycle.run_module_update', fake)

    async def read():
        r = await AsyncClient().get(f'/stream/module-update/alpha/db1/{module}',
                                    headers={'Authorization': f'Token {actors["manager"].token_key}'})
        body = b''
        async for chunk in r.streaming_content:
            body += chunk
        return r.status_code, body.decode()
    status, body = async_to_sync(read)()
    assert status == 200 and seen['args'] == ('alpha', 'db1', module)
    assert 'modules loaded' in body and '"done": true' in body


@pytest.mark.django_db(transaction=True)
def test_a_crashing_update_still_ends_the_stream_and_says_so(actors, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError('container is not running')
    monkeypatch.setattr('apps.streams.views.lifecycle.run_module_update', boom)

    async def read():
        r = await AsyncClient().get('/stream/module-update/alpha/db1/sale',
                                    headers={'Authorization': f'Token {actors["manager"].token_key}'})
        body = b''
        async for chunk in r.streaming_content:
            body += chunk
        return body.decode()
    body = async_to_sync(read)()
    assert 'Update failed: container is not running' in body and '"done": true' in body
