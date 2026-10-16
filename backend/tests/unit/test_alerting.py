import datetime as dt

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.security.models import SecurityAlert
from services.alerting import AlertManager
from services.detection import Event

pytestmark = pytest.mark.django_db


class Recorder:
    def __init__(self):
        self.sent = []

    def notify(self, alert, kind):
        self.sent.append((alert.rule, alert.severity, alert.count, kind))


def ev(rule='pg_auth_failure', severity='warning', key='k1', source='a-db', summary='s', sample='x'):
    return Event(rule=rule, severity=severity, source=source, key=key, summary=summary, sample=sample)


@pytest.fixture
def mgr():
    rec = Recorder()
    return AlertManager(notifiers=[rec], window=dt.timedelta(minutes=15)), rec


def test_first_event_creates_an_open_alert_and_notifies_once(mgr):
    m, rec = mgr
    m.handle(ev())
    assert SecurityAlert.objects.count() == 1
    a = SecurityAlert.objects.get()
    assert a.status == 'open' and a.count == 1 and a.rule == 'pg_auth_failure'
    assert rec.sent == [('pg_auth_failure', 'warning', 1, 'new')]


def test_repeats_inside_the_window_are_aggregated_not_re_announced(mgr):
    m, rec = mgr
    for _ in range(4):
        m.handle(ev())
    a = SecurityAlert.objects.get()
    assert a.count == 4 and len(rec.sent) == 1


def test_a_critical_event_notifies_every_time_it_is_new_but_aggregates_bursts(mgr):
    m, rec = mgr
    for _ in range(10):
        m.handle(ev(rule='pg_copy_program', severity='critical', key='copy:a-db'))
    assert SecurityAlert.objects.count() == 1 and SecurityAlert.objects.get().count == 10
    assert [s[3] for s in rec.sent] == ['new']


def test_warning_escalates_to_high_then_critical_as_the_count_grows(mgr):
    m, rec = mgr
    for _ in range(5):
        m.handle(ev())
    assert SecurityAlert.objects.get().severity == 'high'
    for _ in range(15):
        m.handle(ev())
    assert SecurityAlert.objects.get().severity == 'critical'
    kinds = [s[3] for s in rec.sent]
    assert kinds == ['new', 'escalated', 'escalated']


def test_an_event_after_the_window_opens_a_new_alert(mgr):
    m, rec = mgr
    with freeze_time('2026-10-16 10:00:00'):
        m.handle(ev())
    with freeze_time('2026-10-16 10:30:00'):
        m.handle(ev())
    assert SecurityAlert.objects.count() == 2 and len(rec.sent) == 2


def test_an_acknowledged_alert_is_not_reopened_by_new_events_inside_the_window(mgr):
    m, rec = mgr
    m.handle(ev())
    a = SecurityAlert.objects.get()
    a.status, a.acknowledged_by = 'acknowledged', 'root'
    a.save()
    m.handle(ev())
    assert SecurityAlert.objects.count() == 2 and SecurityAlert.objects.filter(status='open').count() == 1


def test_different_keys_are_separate_alerts(mgr):
    m, _ = mgr
    m.handle(ev(key='k1'))
    m.handle(ev(key='k2'))
    assert SecurityAlert.objects.count() == 2


def test_ignored_sources_are_dropped(mgr):
    m, rec = mgr
    m.ignore = {'192.168.0.13'}
    m.handle(ev(summary='authentication failed for odoo_app from 192.168.0.13', key='pg_auth_failure:x:odoo_app:192.168.0.13'))
    assert SecurityAlert.objects.count() == 0 and rec.sent == []


def test_a_failing_notifier_never_loses_the_alert(mgr):
    m, rec = mgr

    class Boom:
        def notify(self, alert, kind):
            raise RuntimeError('smtp down')
    m.notifiers.insert(0, Boom())
    m.handle(ev())
    assert SecurityAlert.objects.count() == 1 and len(rec.sent) == 1
