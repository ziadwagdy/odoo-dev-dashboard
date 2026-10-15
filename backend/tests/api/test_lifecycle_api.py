"""Phase 2 API: module update snapshots first, restore tests, neutralization badge. Written first."""
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
        'stranger': client_for(make_user('str', role='developer', projects=['beta'])),
    }


def _post(c, path, body=None):
    return c.post(path, json.dumps(body or {}), content_type='application/json')


# ── database list shows neutralization state ───────────────────────────────
def test_database_list_includes_the_neutralized_flag(actors, monkeypatch):
    monkeypatch.setattr('apps.projects.views.list_databases',
                        lambda port: [{'name': 'a', 'size': '1 MB', 'size_bytes': 1}, {'name': 'b', 'size': '2 MB', 'size_bytes': 2}])
    monkeypatch.setattr('apps.projects.views.database_state',
                        lambda port, db: {'neutralized': db == 'a'})
    data = actors['dev'].get('/api/db/alpha/list').json()['databases']
    assert {d['name']: d['neutralized'] for d in data} == {'a': True, 'b': False}


def test_database_list_survives_an_unreadable_database(actors, monkeypatch):
    monkeypatch.setattr('apps.projects.views.list_databases', lambda port: [{'name': 'a', 'size': '1 MB', 'size_bytes': 1}])

    def boom(port, db):
        raise RuntimeError('permission denied')
    monkeypatch.setattr('apps.projects.views.database_state', boom)
    data = actors['dev'].get('/api/db/alpha/list').json()['databases']
    assert data[0]['neutralized'] is None          # unknown, not "false" and not a 500


# ── restore test endpoint ──────────────────────────────────────────────────
@pytest.fixture
def backups(odoo_base, settings, tmp_path):
    settings.DATA_DIR = str(tmp_path / 'data')
    d = tmp_path / 'data' / 'backups' / 'alpha'
    d.mkdir(parents=True)
    (d / 'db1-20261015-000000.dump').write_text('x')
    return d


def test_restore_test_is_manager_or_admin_only(actors, backups, monkeypatch):
    monkeypatch.setattr('apps.projects.views.lifecycle.restore_check',
                        lambda project, port, path, directory: {'ok': True, 'checks': {'users': 3, 'modules': 9}, 'seconds': 4.2, 'error': ''})
    assert _post(actors['dev'], '/api/db/alpha/restore-test').status_code == 403
    assert _post(actors['stranger'], '/api/db/alpha/restore-test').status_code == 403
    r = _post(actors['manager'], '/api/db/alpha/restore-test')
    assert r.status_code == 200 and r.json()['ok'] is True and r.json()['checks']['users'] == 3


def test_restore_test_is_audited_with_the_outcome(actors, backups, monkeypatch):
    monkeypatch.setattr('apps.projects.views.lifecycle.restore_check',
                        lambda project, port, path, directory: {'ok': False, 'checks': {}, 'seconds': 1.0, 'error': 'empty'})
    r = _post(actors['admin'], '/api/db/alpha/restore-test')
    assert r.status_code == 200 and r.json()['ok'] is False
    entry = AuditLog.objects.get(action='restore_test')
    assert entry.outcome == 'failed' and entry.user == 'root' and entry.meta['backup'] == 'db1-20261015-000000.dump'


def test_restore_test_without_any_backup_is_a_404(actors, odoo_base, settings, tmp_path):
    settings.DATA_DIR = str(tmp_path / 'empty')
    assert _post(actors['admin'], '/api/db/alpha/restore-test').status_code == 404


# ── module update streams the snapshot step first ──────────────────────────
@pytest.mark.django_db(transaction=True)
def test_module_update_stream_relays_snapshot_and_update_lines(actors, odoo_base, monkeypatch):
    def fake_update(project, db_port, dbname, module, emit, backup_dir, **kw):
        emit('Taking a safety snapshot before updating…')
        emit(f'update {module} in {dbname}')
        return 0
    monkeypatch.setattr('apps.streams.views.lifecycle.run_module_update', fake_update)

    async def read():
        client = AsyncClient()
        r = await client.get('/stream/module-update/alpha/db1/sale',
                             headers={'Authorization': f'Token {actors["manager"].token_key}'})
        body = b''
        async for chunk in r.streaming_content:
            body += chunk
        return r.status_code, body.decode()
    status, body = async_to_sync(read)()
    assert status == 200
    assert body.index('safety snapshot') < body.index('update sale in db1')
    assert '"done": true' in body
