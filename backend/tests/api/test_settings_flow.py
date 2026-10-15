import json

import pytest

from apps.projects.models import AuditLog, ConfigChangeRequest
from services import settings_schema as S


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    calls = {'restart': [], 'health': True}
    monkeypatch.setattr(S, 'host_resources', lambda: {'cpu_count': 2, 'ram_total_mb': 8000, 'ram_available_mb': 4000})
    monkeypatch.setattr('apps.settings_app.views.restart_container', lambda name: calls['restart'].append(name))
    monkeypatch.setattr('apps.settings_app.views._health_ok', lambda container: calls['health'])
    return calls


@pytest.fixture
def actors(odoo_base, make_user, client_for):
    return {
        'admin': client_for(make_user('root', role='admin')),
        'dev': client_for(make_user('dev', role='developer', projects=['alpha'])),
        'dev2': client_for(make_user('dev2', role='developer', projects=['alpha'])),
        'stranger': client_for(make_user('str', role='developer', projects=['beta'])),
    }


def _post(client, path, body=None):
    return client.post(path, json.dumps(body or {}), content_type='application/json')


def _conf(odoo_base):
    return (odoo_base / 'alpha' / 'config' / 'odoo.conf').read_text()


def test_runtime_view_never_exposes_secrets_or_the_raw_conf(actors):
    r = actors['dev'].get('/api/settings/alpha/runtime')
    assert r.status_code == 200
    text = r.content.decode()
    for secret in ('SUPERSECRET-DB-PASSWORD', 'admin_passwd', 'db_password', 'addons_path', 'm' * 40):
        assert secret not in text
    assert {f['key'] for f in r.json()['fields']} == set(S.SCHEMA)


def test_runtime_view_respects_project_acl(actors):
    assert actors['stranger'].get('/api/settings/alpha/runtime').status_code == 403
    assert actors['admin'].get('/api/settings/alpha/runtime').status_code == 200


def test_the_raw_conf_endpoints_are_gone(actors):
    assert actors['admin'].get('/api/settings/alpha/odoo-conf').status_code == 404
    assert actors['admin'].post('/api/settings/alpha/odoo-conf/write', {}, format='json').status_code == 404


def test_invalid_request_is_rejected_with_reasons(actors):
    r = _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'addons_path': '/evil'}})
    assert r.status_code == 400 and r.json()['errors']
    assert ConfigChangeRequest.objects.count() == 0


def test_valid_request_is_stored_pending_and_conf_is_untouched(actors, odoo_base):
    before = _conf(odoo_base)
    r = _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}, 'reason': 'save RAM'})
    assert r.status_code == 201
    req = ConfigChangeRequest.objects.get()
    assert req.status == 'pending' and req.requested_by == 'dev' and req.previous == {'workers': 2}
    assert _conf(odoo_base) == before
    assert AuditLog.objects.filter(action='config_request', user='dev').exists()


def test_only_admins_can_approve_reject(actors):
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    rid = ConfigChangeRequest.objects.get().id
    assert _post(actors['dev'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True}).status_code == 403
    assert _post(actors['dev'], f'/api/settings/alpha/changes/{rid}/reject').status_code == 403


def test_approval_requires_explicit_confirmation(actors):
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    rid = ConfigChangeRequest.objects.get().id
    assert _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {}).status_code == 400


def test_approval_writes_only_the_requested_keys_restarts_and_audits(actors, odoo_base, fakes):
    before = _conf(odoo_base)
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    rid = ConfigChangeRequest.objects.get().id
    r = _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 200 and r.json()['restarted'] is True
    after = _conf(odoo_base)
    assert 'workers = 1' in after
    assert [l for l in before.splitlines() if l not in after.splitlines()] == ['workers = 2']
    assert fakes['restart'] == ['alpha-app']
    assert ConfigChangeRequest.objects.get().status == 'applied'
    assert AuditLog.objects.filter(action='config_apply', user='root', outcome='success').exists()


def test_warnings_must_be_acknowledged(actors, odoo_base):
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 4}})
    rid = ConfigChangeRequest.objects.get().id
    r = _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 409 and r.json()['needs_warning_ack'] is True
    assert 'workers = 2' in _conf(odoo_base)
    r = _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True, 'accept_warnings': True})
    assert r.status_code == 200 and 'workers = 4' in _conf(odoo_base)


def test_drift_since_the_request_blocks_approval(actors, odoo_base):
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    rid = ConfigChangeRequest.objects.get().id
    S.write_values({'name': 'alpha', 'conf_file': 'alpha/config/odoo.conf'}, {'workers': 3})   # someone else changed it
    r = _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 409 and 'changed since' in r.json()['errors'][0]


def test_unhealthy_app_after_restart_rolls_the_config_back(actors, odoo_base, fakes):
    before = _conf(odoo_base)
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    rid = ConfigChangeRequest.objects.get().id
    fakes['health'] = False
    r = _post(actors['admin'], f'/api/settings/alpha/changes/{rid}/approve', {'confirm': True})
    assert r.status_code == 500
    assert _conf(odoo_base) == before                       # restored
    assert fakes['restart'] == ['alpha-app', 'alpha-app']   # restarted again on the old config
    req = ConfigChangeRequest.objects.get()
    assert req.status == 'failed' and 'restored' in req.result
    assert AuditLog.objects.filter(action='config_apply', outcome='failed').exists()


def test_reject_and_cancel(actors):
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 1}})
    _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 3}})
    first, second = ConfigChangeRequest.objects.order_by('id')
    assert _post(actors['dev2'], f'/api/settings/alpha/changes/{first.id}/cancel').status_code == 403
    assert _post(actors['dev'], f'/api/settings/alpha/changes/{first.id}/cancel').status_code == 200
    assert _post(actors['admin'], f'/api/settings/alpha/changes/{second.id}/reject', {'note': 'no'}).status_code == 200
    assert {r.status for r in ConfigChangeRequest.objects.all()} == {'cancelled', 'rejected'}


def test_pending_requests_per_user_are_capped(actors):
    for w in (1, 3, 4, 5, 6):
        assert _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': w}}).status_code == 201
    assert _post(actors['dev'], '/api/settings/alpha/changes', {'changes': {'workers': 7}}).status_code == 400


def test_stranger_cannot_file_or_see_requests_for_a_project(actors):
    assert _post(actors['stranger'], '/api/settings/alpha/changes', {'changes': {'workers': 1}}).status_code == 403
