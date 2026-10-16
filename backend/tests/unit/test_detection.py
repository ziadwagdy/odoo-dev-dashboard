"""Detection rules as code (Phase 4). Real log lines taken from the 2026-09/10 incident evidence."""
import pytest

from services.detection import detect

COPY_STMT = ("2026-10-14 17:11:54.015 UTC [947531] STATEMENT:  COPY _prog_out FROM PROGRAM "
             "'echo SD0kKHJlYWRsaW5rIC1mIH4pOyBmb3IgcCBpbiAvcHJvYy9bMC05XSo7' ")
COPY_ERR = ("2026-10-14 17:11:54.015 UTC [947531] ERROR:  permission denied to COPY to or from an external program")
COPY_DETAIL = ('2026-10-14 17:11:54.015 UTC [947531] DETAIL:  Only roles with privileges of the '
               '"pg_execute_server_program" role may COPY to or from an external program.')
AUTH_WITH_HOST = ('2026-10-15 20:42:43.517 UTC [1234] odoo_app@postgres 203.0.113.50 '
                  'FATAL:  password authentication failed for user "odoo_app"')
AUTH_NO_HOST = ('2026-10-15 20:42:43.412 UTC [1234] FATAL:  password authentication failed for user "odoo_app"')
HBA = ('2026-10-15 20:42:43.412 UTC [1234] FATAL:  no pg_hba.conf entry for host "198.51.100.9", user "x", database "y"')


def test_copy_program_statement_is_critical():
    e = detect('albadiya-db', COPY_STMT)
    assert e.rule == 'pg_copy_program' and e.severity == 'critical' and e.source == 'albadiya-db'


@pytest.mark.parametrize('line', [COPY_ERR, COPY_DETAIL])
def test_the_denied_copy_error_lines_are_detected_too(line):
    assert detect('albadiya-db', line).rule == 'pg_copy_program'


def test_copy_program_events_share_one_dedupe_key_per_database():
    assert detect('a-db', COPY_STMT).key == detect('a-db', COPY_ERR).key
    assert detect('a-db', COPY_STMT).key != detect('b-db', COPY_STMT).key


def test_the_payload_is_never_copied_into_the_alert():
    e = detect('albadiya-db', COPY_STMT)
    assert 'SD0kKHJl' not in e.summary and 'SD0kKHJl' not in e.sample
    assert len(e.sample) <= 200


def test_auth_failure_extracts_user_and_source_ip_when_logged():
    e = detect('cnc-db', AUTH_WITH_HOST)
    assert e.rule == 'pg_auth_failure' and e.severity == 'warning'
    assert '203.0.113.50' in e.summary and 'odoo_app' in e.summary
    assert e.key == 'pg_auth_failure:cnc-db:odoo_app:203.0.113.50'


def test_auth_failure_without_a_logged_source_still_alerts():
    e = detect('sivas-db', AUTH_NO_HOST)
    assert e.rule == 'pg_auth_failure' and e.key == 'pg_auth_failure:sivas-db:odoo_app:unknown'


def test_no_hba_entry_is_a_high_severity_probe():
    e = detect('iba-db', HBA)
    assert e.rule == 'pg_no_hba_entry' and e.severity == 'high' and '198.51.100.9' in e.summary


@pytest.mark.parametrize('line', [
    '2026-10-15 20:00:00.000 UTC [1] LOG:  database system is ready to accept connections',
    '2026-10-15 20:00:00.000 UTC [1] LOG:  checkpoint starting: time',
    '2026-10-15 20:00:00.000 UTC [7] odoo_app@db 172.26.0.3 LOG:  connection authorized: user=odoo_app database=db',
    '', '   '])
def test_normal_lines_do_not_alert(line):
    assert detect('x-db', line) is None


def test_a_password_in_a_log_line_is_not_echoed():
    line = 'FATAL:  password authentication failed for user "odoo_app" DETAIL: password=hunter2secret'
    e = detect('x-db', line)
    assert 'hunter2secret' not in (e.summary + e.sample)
