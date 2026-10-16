"""Web Push notifier and VAPID keys (Phase 4). Written first."""
import json
import os

import pytest

from apps.security.models import PushSubscription, SecurityAlert
from services import webpush as wp

pytestmark = pytest.mark.django_db


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def fake(subscription_info, data=None, vapid_private_key=None, vapid_claims=None, **kw):
        calls.append({'endpoint': subscription_info['endpoint'], 'data': json.loads(data), 'claims': vapid_claims})
    monkeypatch.setattr(wp, '_send', fake)
    monkeypatch.setattr(wp, 'vapid_private_key_path', lambda: '/nonexistent')
    return calls


@pytest.fixture
def admin_subs(make_user):
    admin = make_user('root', role='admin')
    dev = make_user('dev', role='developer')
    PushSubscription.objects.create(user=admin, endpoint='https://push.example/admin1', p256dh='k', auth='a')
    PushSubscription.objects.create(user=admin, endpoint='https://push.example/admin2', p256dh='k', auth='a')
    PushSubscription.objects.create(user=dev, endpoint='https://push.example/dev1', p256dh='k', auth='a')
    return admin


def mk(severity='critical', count=1, **kw):
    return SecurityAlert.objects.create(rule='pg_copy_program', severity=severity, source='albadiya-db', key='k',
                                        summary='COPY PROGRAM attempt on albadiya-db', sample='SECRET-EVIDENCE-LINE',
                                        count=count, **kw)


def test_critical_alert_pushes_to_every_admin_device_and_nobody_else(sent, admin_subs):
    wp.WebPushNotifier().notify(mk('critical'), 'new')
    assert {c['endpoint'] for c in sent} == {'https://push.example/admin1', 'https://push.example/admin2'}


def test_payload_is_short_and_never_contains_the_evidence_line(sent, admin_subs):
    wp.WebPushNotifier().notify(mk('critical', count=7), 'new')
    data = sent[0]['data']
    assert data['severity'] == 'critical' and data['url'] == '/security'
    assert 'COPY PROGRAM' in data['title'] and '7' in data['body']
    assert 'SECRET-EVIDENCE-LINE' not in json.dumps(data)


def test_new_warnings_stay_in_the_dashboard_only(sent, admin_subs):
    wp.WebPushNotifier().notify(mk('warning'), 'new')
    assert sent == []


def test_escalation_to_high_does_push(sent, admin_subs):
    wp.WebPushNotifier().notify(mk('high', count=5), 'escalated')
    assert len(sent) == 2 and sent[0]['data']['severity'] == 'high'


def test_new_high_alerts_push(sent, admin_subs):
    wp.WebPushNotifier().notify(mk('high'), 'new')
    assert len(sent) == 2


def test_dead_subscriptions_are_removed(monkeypatch, admin_subs):
    class Gone(Exception):
        class response:
            status_code = 410
    monkeypatch.setattr(wp, '_send', lambda *a, **k: (_ for _ in ()).throw(Gone()))
    monkeypatch.setattr(wp, 'vapid_private_key_path', lambda: '/nonexistent')
    monkeypatch.setattr(wp, 'is_gone', lambda exc: getattr(getattr(exc, 'response', None), 'status_code', 0) in (404, 410))
    wp.WebPushNotifier().notify(mk('critical'), 'new')
    assert PushSubscription.objects.filter(user__username='root').count() == 0
    assert PushSubscription.objects.filter(user__username='dev').count() == 1       # untouched


def test_one_failing_device_does_not_block_the_others(monkeypatch, admin_subs):
    got = []

    def flaky(info, data=None, **kw):
        if info['endpoint'].endswith('admin1'):
            raise RuntimeError('timeout')
        got.append(info['endpoint'])
    monkeypatch.setattr(wp, '_send', flaky)
    monkeypatch.setattr(wp, 'vapid_private_key_path', lambda: '/nonexistent')
    wp.WebPushNotifier().notify(mk('critical'), 'new')
    assert got == ['https://push.example/admin2']


def test_vapid_keys_are_generated_once_with_private_permissions(tmp_path, settings):
    settings.DATA_DIR = str(tmp_path)
    pub1 = wp.public_key()
    path = wp.vapid_private_key_path()
    assert oct(os.stat(path).st_mode & 0o777) == '0o600'
    pub2 = wp.public_key()
    assert pub1 == pub2 and len(pub1) > 60 and '=' not in pub1                 # url-safe base64, no padding
