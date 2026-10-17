"""Deleting a project removes everything it owns on the server. Written first."""
import os

import pytest

from apps.projects.models import AuditLog


@pytest.fixture
def stack(odoo_base, settings, monkeypatch, tmp_path):
    """alpha with a compose dir, a per-project DB secret, dashboard backups, and a Dozzle filter."""
    (odoo_base / 'alpha' / 'docker-compose.yml').write_text('services: {}\n')
    (odoo_base / 'alpha' / 'repo').mkdir()
    secrets = odoo_base / 'secrets'
    secrets.mkdir()
    (secrets / 'alpha.pgpass').write_text('*:5432:*:odoo_app:pw\n')
    (secrets / 'beta.pgpass').write_text('*:5432:*:odoo_app:other\n')
    settings.DATA_DIR = str(tmp_path / 'data')
    backups = tmp_path / 'data' / 'backups'
    (backups / 'alpha').mkdir(parents=True)
    (backups / 'alpha' / 'db1-1.dump').write_text('x')
    (backups / 'beta').mkdir()
    (backups / 'beta' / 'db2-1.dump').write_text('x')
    (odoo_base / 'dozzle').mkdir()
    (odoo_base / 'dozzle' / 'docker-compose.yml').write_text('DOZZLE_FILTER: "name=a-app|alpha-app|beta-app"\n')
    calls = []
    monkeypatch.setattr('apps.projects.views.subprocess.run', lambda cmd, **kw: calls.append(cmd))
    return {'base': odoo_base, 'calls': calls, 'backups': backups}


@pytest.fixture
def admin(db, make_user, client_for):
    return client_for(make_user('root', role='admin'))


def test_delete_removes_directory_registry_secret_and_backups_of_that_project_only(stack, admin):
    r = admin.delete('/api/project/alpha/delete')
    assert r.status_code == 200
    base = stack['base']
    assert not (base / 'alpha').exists()
    assert 'alpha|' not in (base / '.port-registry').read_text() and 'beta|' in (base / '.port-registry').read_text()
    assert not (base / 'secrets' / 'alpha.pgpass').exists()              # the DB credential goes too
    assert (base / 'secrets' / 'beta.pgpass').exists()
    assert not (stack['backups'] / 'alpha').exists()                     # and the dashboard-held backups
    assert (stack['backups'] / 'beta' / 'db2-1.dump').exists()


def test_delete_stops_containers_and_removes_volumes_first(stack, admin):
    admin.delete('/api/project/alpha/delete')
    assert ['docker', 'compose', 'down', '-v'] in stack['calls']


def test_delete_cleans_the_log_viewer_filter(stack, admin):
    admin.delete('/api/project/alpha/delete')
    assert 'alpha-app' not in (stack['base'] / 'dozzle' / 'docker-compose.yml').read_text()


def test_delete_is_audited_and_reports_the_manual_steps(stack, admin):
    r = admin.delete('/api/project/alpha/delete')
    assert any('nginx' in c for c in r.json().get('manual_commands', []))
    assert AuditLog.objects.filter(action='project_delete', project='alpha', user='root').exists()


def test_only_admins_can_delete(stack, make_user, client_for):
    mgr = client_for(make_user('mgr', role='manager', projects=['alpha']))
    assert mgr.delete('/api/project/alpha/delete').status_code == 403
    assert (stack['base'] / 'alpha').exists()


def test_unknown_project_is_404(stack, admin):
    assert admin.delete('/api/project/ghost/delete').status_code == 404
