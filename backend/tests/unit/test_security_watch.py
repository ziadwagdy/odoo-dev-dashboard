import pytest

from apps.security.models import SecurityAlert
from services import security_watch

pytestmark = pytest.mark.django_db


def test_watched_containers_come_from_the_registry(odoo_base):
    assert security_watch.containers() == ['alpha-db', 'beta-db']


def test_end_to_end_log_line_to_open_alert(odoo_base):
    """The alert drill: a COPY ... PROGRAM line on a database container becomes an open critical alert."""
    pushed = []

    class Rec:
        def notify(self, alert, kind):
            pushed.append((alert.severity, kind))
    handler = security_watch.make_handler(notifiers=[Rec()])
    from services.log_watcher import consume
    consume('alpha-db', ["2026-10-16 10:00:00.000 UTC [9] STATEMENT:  COPY _prog_out FROM PROGRAM 'echo AAAA | base64 -d | bash'"],
            handler)
    alert = SecurityAlert.objects.get()
    assert alert.severity == 'critical' and alert.source == 'alpha-db' and alert.status == 'open'
    assert 'AAAA' not in alert.sample and pushed == [('critical', 'new')]


def test_ignore_list_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv('SECURITY_IGNORE', '192.168.0.13, 10.0.0.5')
    assert security_watch.ignore_list() == {'192.168.0.13', '10.0.0.5'}
    monkeypatch.delenv('SECURITY_IGNORE')
    assert security_watch.ignore_list() == set()


def test_start_can_be_disabled(monkeypatch):
    monkeypatch.setenv('SECURITY_WATCH', 'off')
    assert security_watch.start() is None
