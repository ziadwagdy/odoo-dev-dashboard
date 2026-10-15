"""Change requests need a second pair of eyes (Phase 1, written first)."""
import json

import pytest

from apps.projects.models import AuditLog, ConfigChangeRequest
from services import settings_schema as S


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(S, 'host_resources', lambda: {'cpu_count': 2, 'ram_total_mb': 8000, 'ram_available_mb': 4000})
    monkeypatch.setattr('apps.settings_app.views.restart_container', lambda name: None)
    monkeypatch.setattr('apps.settings_app.views._health_ok', lambda container: True)


@pytest.fixture
def people(odoo_base, make_user, client_for):
    return {
        'alice': client_for(make_user('alice', role='admin')),
        'bob': client_for(make_user('bob', role='admin')),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
    }


def _post(c, path, body=None):
    return c.post(path, json.dumps(body or {}), content_type='application/json')


def _request_as(client, workers=1):
    r = _post(client, '/api/settings/alpha/changes', {'changes': {'workers': workers}})
    assert r.status_code == 201
    return ConfigChangeRequest.objects.order_by('-id').first().id


def test_an_admin_cannot_approve_their_own_request(people):
    rid = _request_as(people['alice'])
    r = _post(people['alice'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 403
    assert 'own request' in r.json()['errors'][0]
    assert ConfigChangeRequest.objects.get(id=rid).status == 'pending'


def test_another_admin_can_approve(people):
    rid = _request_as(people['alice'])
    r = _post(people['bob'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 200


def test_a_developers_request_can_be_approved_by_any_admin(people):
    rid = _request_as(people['dev'])
    assert _post(people['alice'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True}).status_code == 200


def test_self_approval_is_possible_only_with_an_explicit_override_and_a_reason(people):
    rid = _request_as(people['alice'])
    url = f'/api/settings/alpha/changes/{rid}/approve'
    # override without a reason is refused
    r = _post(people['alice'], url, {'confirm': True, 'self_approve': True})
    assert r.status_code == 400
    assert ConfigChangeRequest.objects.get(id=rid).status == 'pending'
    # override with a reason works and is clearly marked
    r = _post(people['alice'], url, {'confirm': True, 'self_approve': True, 'note': 'sole admin, prod incident 4521'})
    assert r.status_code == 200
    assert AuditLog.objects.filter(action='config_self_approve', user='alice').exists()


def test_the_override_flag_does_not_matter_for_someone_elses_request(people):
    rid = _request_as(people['dev'])
    r = _post(people['alice'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True, 'self_approve': True})
    assert r.status_code == 200
    assert not AuditLog.objects.filter(action='config_self_approve').exists()


def test_the_runtime_view_tells_the_ui_which_requests_the_viewer_may_approve(people):
    rid = _request_as(people['alice'])
    mine = people['alice'].get('/api/settings/alpha/runtime').json()['pending'][0]
    assert mine['id'] == rid and mine['can_approve'] is False and mine['self_request'] is True
    theirs = people['bob'].get('/api/settings/alpha/runtime').json()['pending'][0]
    assert theirs['can_approve'] is True and theirs['self_request'] is False
