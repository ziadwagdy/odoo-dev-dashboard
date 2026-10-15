import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient

pytestmark = pytest.mark.django_db(transaction=True)


def _get(path, token=None, query=''):
    client = AsyncClient()
    headers = {'Authorization': f'Token {token}'} if token else None
    return async_to_sync(client.get)(path + query, headers=headers)


@pytest.fixture
def tokens(odoo_base, make_user, client_for):
    admin = make_user('root', role='admin')
    mgr = make_user('mgr', role='manager', projects=['alpha'])
    dev = make_user('dev', role='developer', projects=['alpha'])
    stranger = make_user('str', role='developer', projects=[])
    return {n: client_for(u).token_key for n, u in
            (('admin', admin), ('manager', mgr), ('dev', dev), ('stranger', stranger))}


@pytest.mark.parametrize('path', [
    '/stream/status', '/stream/health/host', '/stream/deploy/alpha', '/stream/logs/alpha-app',
    '/stream/git-pull/alpha', '/stream/module-update/alpha/db1/base', '/api/onboard/stream/alpha'])
def test_every_stream_requires_authentication(odoo_base, path):
    assert _get(path).status_code == 401
    assert _get(path, token='not-a-token').status_code == 401


def test_token_in_query_string_is_accepted(odoo_base, tokens):
    assert _get('/stream/deploy/alpha', query=f"?token={tokens['dev']}").status_code == 200


def test_project_acl_is_enforced(tokens):
    assert _get('/stream/deploy/alpha', tokens['dev']).status_code == 200
    assert _get('/stream/deploy/alpha', tokens['stranger']).status_code == 403
    assert _get('/stream/deploy/alpha', tokens['admin']).status_code == 200


def test_unknown_project_is_404(tokens):
    assert _get('/stream/deploy/ghost', tokens['admin']).status_code == 404


def test_mutating_streams_need_manager_or_admin(tokens, monkeypatch):
    path = '/stream/git-pull/alpha'
    assert _get(path, tokens['dev']).status_code == 403
    assert _get(path, tokens['manager']).status_code == 200


def test_onboarding_stream_is_admin_only(tokens):
    assert _get('/api/onboard/stream/alpha', tokens['manager']).status_code == 403
    assert _get('/api/onboard/stream/alpha', tokens['admin']).status_code == 200


@pytest.mark.parametrize('bad', ['a%3Bb', 'x%20y', '..%2Fetc', '$(id)'])
def test_parameters_that_could_reach_docker_exec_are_rejected(tokens, bad):
    r = _get(f'/stream/module-update/alpha/{bad}/base', tokens['admin'])
    assert r.status_code in (400, 404)


def test_container_logs_for_non_project_containers_are_admin_only(tokens):
    assert _get('/stream/logs/odoo-logs', tokens['dev']).status_code == 403
