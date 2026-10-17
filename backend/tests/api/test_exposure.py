"""Least exposure: show users what they use, nothing about the host. Written first."""
import json

import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient

FORBIDDEN = {'odoo_port', 'db_port', 'folder', 'conf_file', 'addons_paths'}


@pytest.fixture
def people(odoo_base, make_user, client_for, monkeypatch):
    monkeypatch.setattr('apps.projects.views.get_container_status', lambda c: 'running')
    monkeypatch.setattr('apps.projects.views.get_git_info', lambda folder: ('main', []))
    monkeypatch.setattr('apps.projects.views.get_commit_log', lambda folder, n=10: [])
    monkeypatch.setattr('apps.projects.views.get_addons_path', lambda *a, **k: [{'path': '/mnt/x'}])

    class FakeContainer:
        short_id = 'abc123def456'

    class FakeDocker:
        class containers:
            @staticmethod
            def get(name):
                return FakeContainer()
    monkeypatch.setattr('apps.projects.views.get_docker_client', lambda: FakeDocker)
    return {
        'admin': client_for(make_user('root', role='admin')),
        'manager': client_for(make_user('mgr', role='manager', projects=['alpha'])),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
    }


@pytest.mark.parametrize('role', ['admin', 'manager', 'dev'])
def test_project_detail_never_exposes_ports_or_host_paths(people, role):
    data = people[role].get('/api/project/alpha').json()
    assert not (FORBIDDEN & set(data)), f'leaked: {FORBIDDEN & set(data)}'
    text = json.dumps(data)
    for token in ('/mnt/', '/home/', '15432', '8069', 'odoo-dev/'):
        assert token not in text, f'{token} leaked in the project payload'


@pytest.mark.parametrize('role', ['admin', 'manager', 'dev'])
def test_status_list_never_exposes_ports_or_host_paths(people, role):
    for p in people[role].get('/api/status').json()['projects']:
        assert not (FORBIDDEN & set(p)), f'leaked: {FORBIDDEN & set(p)}'


def test_what_the_ui_needs_is_still_there(people):
    data = people['dev'].get('/api/project/alpha').json()
    for key in ('name', 'version', 'url', 'container', 'status', 'running', 'branch', 'pending_count', 'commits', 'uses_hr_base'):
        assert key in data, key
    assert data['uses_hr_base'] is False


def test_hr_base_projects_are_flagged_without_revealing_the_path(people, odoo_base):
    (odoo_base / '.port-registry').write_text(
        'alpha|18|8069|15432|alpha.example.org|worktrees/hr-base-18|alpha/config/odoo.conf\n')
    assert people['dev'].get('/api/project/alpha').json()['uses_hr_base'] is True


def test_container_id_is_for_admins_only(people):
    assert people['admin'].get('/api/project/alpha').json().get('container_id') == 'abc123def456'
    assert 'container_id' not in people['manager'].get('/api/project/alpha').json()
    assert 'container_id' not in people['dev'].get('/api/project/alpha').json()


# ── /api/config: internal tool URLs are not public ─────────────────────────
def test_anonymous_config_has_only_the_title(anon):
    data = anon.get('/api/config').json()
    assert set(data) == {'dashboard_title'}


def test_non_admins_get_no_tool_urls(people):
    assert set(people['dev'].get('/api/config').json()) == {'dashboard_title'}
    assert set(people['manager'].get('/api/config').json()) == {'dashboard_title'}


def test_admins_get_the_tool_urls(people):
    assert {'logs_url', 'files_url', 'terminal_url'} <= set(people['admin'].get('/api/config').json())


# ── server-wide numbers are for managers and admins ────────────────────────
def test_storage_hides_host_disk_figures_from_developers(people, monkeypatch):
    monkeypatch.setattr('apps.projects.views.get_all_project_storage', lambda projects: [])
    dev = people['dev'].get('/api/storage').json()
    assert 'disk_used_gb' not in dev and 'disk_total_gb' not in dev and 'disk_pct' not in dev
    mgr = people['manager'].get('/api/storage').json()
    assert 'disk_used_gb' in mgr


@pytest.mark.django_db(transaction=True)
def test_host_health_stream_is_for_managers_and_admins(people, monkeypatch):
    monkeypatch.setattr('apps.streams.views.get_host_stats', lambda: {'cpu_pct': 1})

    async def hit(role):
        r = await AsyncClient().get('/stream/health/host', headers={'Authorization': f'Token {people[role].token_key}'})
        return r.status_code
    assert async_to_sync(hit)('dev') == 403
    assert async_to_sync(hit)('manager') == 200
