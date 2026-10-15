import pytest
from django.core.cache import cache
from rest_framework.authtoken.models import Token

from apps.projects.models import AuditLog

PW = 'correct-horse-battery-staple'


def _login(client, username, password, **extra):
    return client.post('/api/auth/login', {'username': username, 'password': password}, format='json', **extra)


def test_login_returns_token_and_role_and_is_audited(anon, make_user):
    make_user('ana', role='manager')
    r = _login(anon, 'ana', PW)
    assert r.status_code == 200
    assert r.json()['role'] == 'manager' and r.json()['token']
    assert AuditLog.objects.filter(action='login', user='ana', outcome='success').exists()


def test_failed_login_is_audited_with_client_ip(anon, make_user):
    make_user('ana')
    r = _login(anon, 'ana', 'wrong', HTTP_CF_CONNECTING_IP='203.0.113.9')
    assert r.status_code == 401
    entry = AuditLog.objects.get(action='login', outcome='failed')
    assert '203.0.113.9' in entry.detail


def test_lockout_after_five_failures_even_with_the_right_password(anon, make_user):
    make_user('ana')
    for _ in range(5):
        assert _login(anon, 'ana', 'wrong').status_code == 401
    assert _login(anon, 'ana', PW).status_code == 429
    assert AuditLog.objects.filter(action='login_blocked').exists()


def test_successful_login_resets_the_failure_counter(anon, make_user):
    make_user('ana')
    for _ in range(4):
        _login(anon, 'ana', 'wrong')
    assert _login(anon, 'ana', PW).status_code == 200
    for _ in range(4):
        assert _login(anon, 'ana', 'wrong').status_code == 401   # counter restarted, not at 5


def test_ip_level_lockout_blocks_username_spraying(anon, make_user):
    make_user('ana')
    for i in range(30):
        _login(anon, f'ghost{i}', 'x', HTTP_CF_CONNECTING_IP='198.51.100.7')
    assert _login(anon, 'ana', PW, HTTP_CF_CONNECTING_IP='198.51.100.7').status_code == 429
    assert _login(anon, 'ana', PW, HTTP_CF_CONNECTING_IP='198.51.100.8').status_code == 200


def test_each_login_issues_a_new_token_and_kills_the_old_one(anon, make_user):
    make_user('ana')
    first = _login(anon, 'ana', PW).json()['token']
    second = _login(anon, 'ana', PW).json()['token']
    assert first != second
    assert not Token.objects.filter(key=first).exists()


def test_logout_invalidates_the_token(make_user, client_for, anon):
    c = client_for(make_user('ana'))
    assert c.post('/api/auth/logout').status_code == 200
    assert c.get('/api/auth/me').status_code == 401


def test_requests_without_or_with_bad_tokens_are_401(anon):
    assert anon.get('/api/auth/me').status_code == 401
    anon.credentials(HTTP_AUTHORIZATION='Token nope')
    assert anon.get('/api/auth/me').status_code == 401


@pytest.mark.parametrize('weak', ['short', '1234567890123', 'aaaaaaaaaaaaaaaa', 'ana'])
def test_password_policy_on_user_creation(make_user, client_for, weak):
    admin = client_for(make_user('root', role='admin'))
    r = admin.post('/api/auth/users/create', {'username': 'bob', 'password': weak, 'role': 'developer'}, format='json')
    assert r.status_code == 400


def test_admin_can_create_a_user_with_a_strong_password(make_user, client_for):
    admin = client_for(make_user('root', role='admin'))
    r = admin.post('/api/auth/users/create', {'username': 'bob', 'password': PW, 'role': 'developer'}, format='json')
    assert r.status_code == 201


def test_non_admin_cannot_create_users(make_user, client_for):
    dev = client_for(make_user('dev', role='developer'))
    r = dev.post('/api/auth/users/create', {'username': 'bob', 'password': PW, 'role': 'admin'}, format='json')
    assert r.status_code == 403


def test_change_password_policy_and_session_invalidation(make_user, client_for):
    user = make_user('ana')
    c = client_for(user)
    assert c.post(f'/api/auth/users/{user.id}/password', {'password': 'short'}, format='json').status_code == 400
    assert c.post(f'/api/auth/users/{user.id}/password', {'password': 'a-much-better-passphrase'}, format='json').status_code == 200
    assert c.get('/api/auth/me').status_code == 401        # the old session is gone


def test_a_user_cannot_change_someone_elses_password(make_user, client_for):
    a, b = make_user('a'), make_user('b')
    r = client_for(a).post(f'/api/auth/users/{b.id}/password', {'password': 'a-much-better-passphrase'}, format='json')
    assert r.status_code == 403


def test_admin_can_revoke_sessions_and_it_is_audited(make_user, client_for):
    victim = make_user('vic')
    victim_client = client_for(victim)
    admin = client_for(make_user('root', role='admin'))
    r = admin.post(f'/api/auth/users/{victim.id}/revoke-sessions')
    assert r.status_code == 200 and r.json()['revoked'] == 1
    assert victim_client.get('/api/auth/me').status_code == 401
    assert AuditLog.objects.filter(action='session_revoke', user='root').exists()


def test_revoke_sessions_requires_admin(make_user, client_for):
    victim = make_user('vic')
    assert client_for(make_user('mgr', role='manager')).post(f'/api/auth/users/{victim.id}/revoke-sessions').status_code == 403
