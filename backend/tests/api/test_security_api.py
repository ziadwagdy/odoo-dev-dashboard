import json

import pytest

from apps.security.models import SecurityAlert


@pytest.fixture
def people(db, make_user, client_for):
    return {
        'admin': client_for(make_user('root', role='admin')),
        'manager': client_for(make_user('mgr', role='manager')),
        'dev': client_for(make_user('dev', role='developer')),
    }


@pytest.fixture
def alerts(db):
    SecurityAlert.objects.create(rule='pg_copy_program', severity='critical', source='albadiya-db', key='copy:albadiya-db', summary='COPY PROGRAM attempt', sample='x', count=3)
    SecurityAlert.objects.create(rule='pg_auth_failure', severity='warning', source='cnc-db', key='auth:cnc', summary='auth failure', sample='y', count=1)


def test_only_admins_see_security_alerts(people, alerts):
    assert people['admin'].get('/api/security/alerts').status_code == 200
    assert people['manager'].get('/api/security/alerts').status_code == 403
    assert people['dev'].get('/api/security/alerts').status_code == 403


def test_unauthenticated_access_is_refused(anon):
    assert anon.get('/api/security/alerts').status_code == 401
    assert anon.get('/api/security/summary').status_code == 401


def test_alerts_are_sorted_by_severity_then_recency(people, alerts):
    data = people['admin'].get('/api/security/alerts').json()['alerts']
    assert [a['severity'] for a in data] == ['critical', 'warning']


def test_summary_drives_the_header_badge(people, alerts):
    s = people['admin'].get('/api/security/summary').json()
    assert s == {'open': 2, 'critical': 1, 'high': 0, 'worst': 'critical'}


def test_summary_is_calm_when_there_is_nothing_open(people):
    assert people['admin'].get('/api/security/summary').json() == {'open': 0, 'critical': 0, 'high': 0, 'worst': None}


def test_acknowledge_records_who_and_when(people, alerts):
    a = SecurityAlert.objects.get(rule='pg_copy_program')
    r = people['admin'].post(f'/api/security/alerts/{a.id}/ack', json.dumps({'note': 'investigated, own probe'}), content_type='application/json')
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.status == 'acknowledged' and a.acknowledged_by == 'root' and a.note == 'investigated, own probe'
    assert people['admin'].get('/api/security/summary').json()['open'] == 1


def test_only_admins_can_acknowledge(people, alerts):
    a = SecurityAlert.objects.first()
    assert people['manager'].post(f'/api/security/alerts/{a.id}/ack').status_code == 403
