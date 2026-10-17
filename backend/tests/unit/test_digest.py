import pytest

from apps.security.models import SecurityAlert
from services import digest

pytestmark = pytest.mark.django_db


def mk(sev, status='open'):
    return SecurityAlert.objects.create(rule='r', severity=sev, source='s', key=f'{sev}{status}{SecurityAlert.objects.count()}',
                                        summary='x', status=status)


def test_digest_counts_only_open_alerts():
    mk('critical'); mk('high'); mk('warning'); mk('critical', status='acknowledged')
    d = digest.build_digest()
    assert d == {'open': 3, 'critical': 1, 'high': 1, 'warning': 1}


def test_nothing_is_sent_when_there_is_nothing_open():
    sent = []
    assert digest.send_daily_digest(lambda title, body, severity: sent.append((title, body, severity))) is False
    assert sent == []


def test_a_summary_is_sent_when_alerts_are_open_with_the_worst_severity():
    mk('critical'); mk('warning'); mk('warning')
    sent = []
    assert digest.send_daily_digest(lambda title, body, severity: sent.append((title, body, severity))) is True
    title, body, severity = sent[0]
    assert '3' in title and severity == 'critical'
    assert '1 critical' in body and '2 warning' in body
