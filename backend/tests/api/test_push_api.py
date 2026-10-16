import json

import pytest

from apps.security.models import PushSubscription

SUB = {'endpoint': 'https://push.example/abc', 'keys': {'p256dh': 'BKey', 'auth': 'authsecret'}}


@pytest.fixture
def people(db, make_user, client_for):
    return {'admin': client_for(make_user('root', role='admin')),
            'dev': client_for(make_user('dev', role='developer'))}


def _post(c, path, body=None):
    return c.post(path, json.dumps(body or {}), content_type='application/json')


def test_public_key_is_available_to_admins_only(people, monkeypatch, tmp_path, settings):
    settings.DATA_DIR = str(tmp_path)
    r = people['admin'].get('/api/push/public-key')
    assert r.status_code == 200 and len(r.json()['key']) > 60
    assert people['dev'].get('/api/push/public-key').status_code == 403


def test_subscribe_stores_the_device_for_the_admin(people):
    r = _post(people['admin'], '/api/push/subscribe', SUB)
    assert r.status_code == 200
    s = PushSubscription.objects.get()
    assert s.user.username == 'root' and s.endpoint == SUB['endpoint'] and s.auth == 'authsecret'


def test_subscribing_twice_is_idempotent(people):
    _post(people['admin'], '/api/push/subscribe', SUB)
    _post(people['admin'], '/api/push/subscribe', SUB)
    assert PushSubscription.objects.count() == 1


def test_non_admins_cannot_subscribe(people):
    assert _post(people['dev'], '/api/push/subscribe', SUB).status_code == 403
    assert PushSubscription.objects.count() == 0


def test_malformed_subscriptions_are_rejected(people):
    assert _post(people['admin'], '/api/push/subscribe', {'endpoint': 'http://insecure/x', 'keys': SUB['keys']}).status_code == 400
    assert _post(people['admin'], '/api/push/subscribe', {'endpoint': SUB['endpoint']}).status_code == 400


def test_unsubscribe_removes_only_that_device(people):
    _post(people['admin'], '/api/push/subscribe', SUB)
    _post(people['admin'], '/api/push/subscribe', {**SUB, 'endpoint': 'https://push.example/other'})
    assert _post(people['admin'], '/api/push/unsubscribe', {'endpoint': SUB['endpoint']}).status_code == 200
    assert [s.endpoint for s in PushSubscription.objects.all()] == ['https://push.example/other']


def test_test_notification_goes_to_the_callers_devices(people, monkeypatch):
    sent = []
    monkeypatch.setattr('apps.security.push_views.webpush_service.send_to_user',
                        lambda user, title, body, severity='info', url='/security': sent.append((user.username, title)) or 1)
    _post(people['admin'], '/api/push/subscribe', SUB)
    r = _post(people['admin'], '/api/push/test')
    assert r.status_code == 200 and sent and sent[0][0] == 'root'
